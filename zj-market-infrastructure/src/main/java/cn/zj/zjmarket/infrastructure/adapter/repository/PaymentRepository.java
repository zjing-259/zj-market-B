package cn.zj.zjmarket.infrastructure.adapter.repository;

import cn.zj.zjmarket.domain.payment.adapter.repository.IPaymentRepository;
import cn.zj.zjmarket.domain.payment.model.valobj.*;
import cn.zj.zjmarket.domain.order.adapter.repository.IOrderRepository;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
import cn.zj.zjmarket.domain.order.service.impl.OrderService;
import cn.zj.zjmarket.types.exception.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.*;
import org.springframework.transaction.support.TransactionTemplate;
import javax.sql.DataSource;
import java.util.*;

/** Market transactions only. Calls to A and the channel belong outside this repository. */
public final class PaymentRepository implements IPaymentRepository {
 private final JdbcTemplate db;
 private final TransactionTemplate tx;
 private final IOrderRepository orders;
 private final ObjectMapper json = new ObjectMapper();
 private static final String NOW="CAST(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3))*1000 AS SIGNED)";
 public PaymentRepository(DataSource source,TransactionTemplate tx,IOrderRepository orders){db=new JdbcTemplate(source);this.tx=tx;this.orders=orders;}
 public long now(){return db.queryForObject("SELECT "+NOW,Long.class);}
 private <T>T first(String sql,RowMapper<T> mapper,Object...args){var rows=db.query(sql,mapper,args);return rows.isEmpty()?null:rows.getFirst();}
 private static Long nullable(java.sql.ResultSet rs,String field)throws java.sql.SQLException{long value=rs.getLong(field);return rs.wasNull()?null:value;}
 private final RowMapper<Payment> paymentMapper=(rs,n)->new Payment(rs.getString("payment_id"),rs.getString("order_id"),rs.getString("user_id"),rs.getLong("version"),rs.getString("funds_state"),rs.getString("gate"),rs.getString("a_acceptance"),rs.getBigDecimal("amount").toPlainString(),rs.getString("currency"),rs.getLong("payment_deadline_ms"),nullable(rs,"paid_at_ms"),rs.getString("active_attempt_id"),rs.getString("success_attempt_id"),rs.getBoolean("review_required"),rs.getString("last_error"));
 private final RowMapper<Attempt> attemptMapper=(rs,n)->new Attempt(rs.getString("attempt_id"),rs.getString("payment_id"),rs.getInt("attempt_no"),rs.getLong("version"),rs.getString("state"),rs.getBigDecimal("amount").toPlainString(),rs.getLong("payment_deadline_ms"),nullable(rs,"paid_at_ms"),rs.getString("channel_transaction_id"),rs.getString("last_error"));
 public MarketOrder order(String actor,String id){var o=orders.byId(actor,id);if(o==null)throw new OrderFailure(404,"ORDER_NOT_FOUND");return o;}
 public Payment payment(String actor,String id){var p=first("SELECT * FROM b_payment WHERE user_id=? AND payment_id=?",paymentMapper,actor,id);if(p==null)throw new OrderFailure(404,"PAYMENT_NOT_FOUND");return p;}
 public Payment forOrder(String actor,String id){return first("SELECT * FROM b_payment WHERE user_id=? AND order_id=?",paymentMapper,actor,id);}
 public List<Attempt> attempts(String id){return db.query("SELECT * FROM b_payment_attempt WHERE payment_id=? ORDER BY attempt_no DESC LIMIT 20",attemptMapper,id);}
 public Attempt attempt(String payment,String attempt){return first("SELECT * FROM b_payment_attempt WHERE payment_id=? AND attempt_id=?",attemptMapper,payment,attempt);}
 public boolean canDispatch(Work work){return Boolean.TRUE.equals(tx.execute(s->fence(work)&&rejection(order(work.actor(),work.orderId()))==null&&payment(work.actor(),work.paymentId()).gate().equals("OPEN")));}
 public Operation operation(String actor,String key){return first("SELECT request_hash,receipt_json,progress,SHA2(CAST(receipt_json AS CHAR),256)=receipt_hash AS intact FROM b_payment_operation WHERE actor_id=? AND operation_key=?",(rs,n)->{if(!rs.getBoolean("intact"))throw new IllegalStateException("Payment receipt audit mismatch");return new Operation(rs.getString(1),decode(rs.getString(2),Receipt.class),rs.getString(3));},actor,key);}
 private MarketOrder lock(String actor,String id){
  var before=order(actor,id);String goods=before.confirmation().conditions().goodsId();
  var enabled=first("SELECT enabled FROM b_user WHERE user_id=? FOR UPDATE",(rs,n)->rs.getBoolean(1),actor);
  if(enabled==null)throw new IllegalStateException("Missing payment owner");
  db.queryForList("SELECT goods_id FROM b_product WHERE goods_id=? FOR UPDATE",goods);
  String active=first("SELECT active_order_id FROM b_purchase_guard WHERE user_id=? AND goods_id=? FOR UPDATE",(rs,n)->rs.getString(1),actor,goods);
  db.queryForList("SELECT goods_id FROM b_inventory_account WHERE goods_id=? FOR UPDATE",goods);
  db.queryForList("SELECT order_id FROM b_market_order WHERE order_id=? FOR UPDATE",id);
  String reservation=first("SELECT state FROM b_inventory_reservation WHERE order_id=? FOR UPDATE",(rs,n)->rs.getString(1),id);
  db.queryForList("SELECT order_id FROM b_trade_coordination WHERE order_id=? FOR UPDATE",id);
  var o=order(actor,id);
  // Retain the lock even when returning a durable rejection. Claim/finish must also be able to observe reviewed orders.
  if(!id.equals(active)||!"HELD".equals(reservation))return o;
  return o;
 }
 private String rejection(MarketOrder o){
  if(o.reviewRequired()||!"WAITING_PAYMENT".equals(o.businessStatus())||o.evidence()==null)return "PAYMENT_NOT_ALLOWED";
  if(!o.orderId().equals(first("SELECT active_order_id FROM b_purchase_guard WHERE user_id=? AND goods_id=?",(rs,n)->rs.getString(1),o.confirmation().userId(),o.confirmation().conditions().goodsId())))return "PAYMENT_NOT_ALLOWED";
  if(!"HELD".equals(first("SELECT state FROM b_inventory_reservation WHERE order_id=?",(rs,n)->rs.getString(1),o.orderId())))return "PAYMENT_NOT_ALLOWED";
  if(first("SELECT close_request FROM b_market_order WHERE order_id=?",(rs,n)->rs.getString(1),o.orderId())!=null)return "PAYMENT_NOT_ALLOWED";
  var cursor=first("SELECT status,review_required FROM b_team_cursor WHERE source=? AND channel=? AND team_id=?",(rs,n)->rs.getBoolean("review_required")||!rs.getString("status").equals("FORMING"),o.confirmation().source(),o.confirmation().channel(),o.evidence().teamId());
  if(Boolean.TRUE.equals(cursor))return "PAYMENT_NOT_ALLOWED";
  var t=first("SELECT paused OR run_state<>'DONE' OR intent<>'NONE' FROM b_trade_coordination WHERE order_id=?",(rs,n)->rs.getBoolean(1),o.orderId());
  return Boolean.TRUE.equals(t)?"PAYMENT_NOT_ALLOWED":null;
 }
 public Accepted accept(String actor,String order,String requestedPayment,String requestedAttempt,String key,String previous,String result,String hash,Evidence evidence){
  return tx.execute(status->{
   String paymentId=requestedPayment,attemptId=requestedAttempt;
   var o=lock(actor,order);if(!Boolean.TRUE.equals(first("SELECT enabled FROM b_user WHERE user_id=?",(rs,n)->rs.getBoolean(1),actor)))throw new AuthFailure(401,"AUTH_REQUIRED");var p=first("SELECT * FROM b_payment WHERE order_id=? FOR UPDATE",paymentMapper,order);
   if(p!=null)db.queryForList("SELECT attempt_id FROM b_payment_attempt WHERE payment_id=? ORDER BY attempt_no FOR UPDATE",p.paymentId());
   var old=operation(actor,key);if(old!=null){if(!old.hash().equals(hash))throw new OrderFailure(409,"IDEMPOTENCY_CONFLICT");return new Accepted(old.receipt(),true);}
   long now=now();String action=result==null?"CREATE_ATTEMPT":"CHOOSE_RESULT",error=rejection(o);
   if(error==null){if(evidence==null)throw new OrderFailure(503,"PAYMENT_TIME_UNVERIFIABLE");evidence.validate(o,now);}
   Attempt active=p==null||p.activeAttemptId()==null?null:first("SELECT * FROM b_payment_attempt WHERE payment_id=? AND attempt_id=?",attemptMapper,p.paymentId(),p.activeAttemptId());
   if(error==null&&p!=null&&(!p.gate().equals("OPEN")||p.reviewRequired()))error="PAYMENT_NOT_ALLOWED";
   if(result==null){
    if(error==null&&(p!=null&&!p.fundsState().equals("UNPAID")||active!=null&&!active.state().equals("FAILED")))error="PAYMENT_ATTEMPT_ACTIVE";
    if(error==null&&!Objects.equals(previous,active==null?null:active.attemptId()))error="PAYMENT_PREDECESSOR_CONFLICT";
    if(error==null){
     if(p==null){paymentId=UUID.randomUUID().toString();String snapshot=encode(o);var a=o.evidence();
      one(db.update("INSERT INTO b_payment(payment_id,order_id,user_id,goods_id,snapshot,snapshot_hash,amount,reserved_at_ms,payment_deadline_ms,created_at_ms,updated_at_ms) VALUES(?,?,?,?,?,?,?,?,?,?,?)",paymentId,order,actor,o.confirmation().conditions().goodsId(),snapshot,OrderService.hash(snapshot),a.payPrice(),cn.zj.zjmarket.domain.order.model.valobj.ReservationEvidence.instant(a.reservedAt()),cn.zj.zjmarket.domain.order.model.valobj.ReservationEvidence.instant(a.paymentDeadline()),now,now));
     }else paymentId=p.paymentId();
     attemptId=UUID.randomUUID().toString();int number=active==null?1:Math.addExact(active.attemptNo(),1);String body=encode(Map.of("paymentId",paymentId,"attemptId",attemptId,"attemptNo",number));
     one(db.update("INSERT INTO b_payment_attempt(attempt_id,payment_id,attempt_no,previous_attempt_id,request_json,request_hash,amount,payment_deadline_ms,created_at_ms,updated_at_ms) VALUES(?,?,?,?,?,?,?,?,?,?)",attemptId,paymentId,number,previous,body,OrderService.hash(body),o.evidence().payPrice(),cn.zj.zjmarket.domain.order.model.valobj.ReservationEvidence.instant(o.evidence().paymentDeadline()),now,now));
     one(db.update("UPDATE b_payment SET active_attempt_id=?,version=version+1,updated_at_ms=?,last_error=NULL WHERE payment_id=?",attemptId,now,paymentId));
     // This marker and the durable work commit before any channel call. It can never return to NEVER_OPENED.
     one(db.update("UPDATE b_market_order SET payment_exposure='POSSIBLY_OPENED',order_version=order_version+1,updated_at_ms=? WHERE order_id=? AND close_request IS NULL",now,order));
     task(paymentId,attemptId,action,null,now);
    }
   }else{
    if(error==null&&(p==null||!p.paymentId().equals(paymentId)||active==null||!active.attemptId().equals(attemptId)))error="PAYMENT_ATTEMPT_NOT_ACTIVE";
    String chosen=p==null?null:first("SELECT chosen_result FROM b_payment_operation WHERE payment_id=? AND attempt_id=? AND action='CHOOSE_RESULT' AND progress<>'REJECTED' ORDER BY created_at_ms LIMIT 1",(rs,n)->rs.getString(1),paymentId,attemptId);
    if(error==null&&chosen!=null&&!chosen.equals(result))error="PAYMENT_RESULT_CONFLICT";
    if(error==null&&chosen==null&&!active.state().equals("OPEN"))error="PAYMENT_RESULT_NOT_ALLOWED";
    if(error==null&&chosen==null){one(db.update("UPDATE b_payment_attempt SET state='UNKNOWN',version=version+1,updated_at_ms=? WHERE attempt_id=?",now,attemptId));one(db.update("UPDATE b_payment SET funds_state='UNKNOWN',version=version+1,updated_at_ms=? WHERE payment_id=?",now,paymentId));task(paymentId,attemptId,action,result,now);}
   }
   var receipt=new Receipt(key,action,order,paymentId,attemptId,error==null,now,error);
   String progress=error==null?"PENDING":"REJECTED";
   if(error==null&&result!=null&&active!=null&&Set.of("FAILED","SUCCEEDED").contains(active.state()))progress="APPLIED";
   one(db.update("INSERT INTO b_payment_operation(operation_id,actor_id,operation_key,order_id,payment_id,attempt_id,action,chosen_result,request_hash,receipt_json,receipt_hash,progress,created_at_ms) VALUES(?,?,?,?,?,?,?,?,?,?,SHA2(CAST(CAST(? AS JSON) AS CHAR),256),?,?)",UUID.randomUUID().toString(),actor,key,order,paymentId,attemptId,action,result,hash,encode(receipt),encode(receipt),progress,now));
   return new Accepted(receipt,false,progress.equals("APPLIED"));
  });
 }
 private void task(String payment,String attempt,String action,String result,long now){db.update("INSERT INTO b_payment_task(payment_id,attempt_id,action,chosen_result,state,next_attempt_ms) VALUES(?,?,?,?,'READY',?) ON DUPLICATE KEY UPDATE attempt_id=VALUES(attempt_id),action=VALUES(action),chosen_result=VALUES(chosen_result),intent_version=intent_version+1,state='READY',next_attempt_ms=VALUES(next_attempt_ms),lease_token=NULL,lease_until_ms=NULL,last_error=NULL",payment,attempt,action,result,now);}
 public List<String> due(int size){return db.queryForList("SELECT payment_id FROM b_payment_task WHERE state IN ('READY','WAITING_DEPENDENCY','LEASED') AND next_attempt_ms<="+NOW+" AND (lease_until_ms IS NULL OR lease_until_ms<="+NOW+") ORDER BY next_attempt_ms,payment_id LIMIT ?",String.class,size);}
 private Payment locate(String id){return first("SELECT * FROM b_payment WHERE payment_id=?",paymentMapper,id);}
 public Work claim(String id){var p=locate(id);if(p==null)return null;return tx.execute(s->{lock(p.userId(),p.orderId());db.queryForList("SELECT payment_id FROM b_payment WHERE payment_id=? FOR UPDATE",id);db.queryForList("SELECT attempt_id FROM b_payment_attempt WHERE payment_id=? ORDER BY attempt_no FOR UPDATE",id);var w=first("SELECT * FROM b_payment_task WHERE payment_id=? FOR UPDATE",(rs,n)->new Work(id,rs.getString("attempt_id"),p.userId(),p.orderId(),rs.getString("action"),rs.getString("chosen_result"),rs.getLong("intent_version"),UUID.randomUUID().toString()),id);if(w==null)return null;long now=now();int changed=db.update("UPDATE b_payment_task SET state='LEASED',lease_token=?,lease_until_ms=? WHERE payment_id=? AND state IN ('READY','WAITING_DEPENDENCY','LEASED') AND next_attempt_ms<=? AND (lease_until_ms IS NULL OR lease_until_ms<=?)",w.token(),now+30000,id,now,now);return changed==1?w:null;});}
 private boolean fence(Work w){lock(w.actor(),w.orderId());db.queryForList("SELECT payment_id FROM b_payment WHERE payment_id=? FOR UPDATE",w.paymentId());db.queryForList("SELECT attempt_id FROM b_payment_attempt WHERE payment_id=? ORDER BY attempt_no FOR UPDATE",w.paymentId());db.queryForList("SELECT operation_id FROM b_payment_operation WHERE payment_id=? ORDER BY created_at_ms,operation_id FOR UPDATE",w.paymentId());return Boolean.TRUE.equals(first("SELECT state='LEASED' AND lease_token=? AND intent_version=? AND lease_until_ms>"+NOW+" FROM b_payment_task WHERE payment_id=? FOR UPDATE",(rs,n)->rs.getBoolean(1),w.token(),w.intentVersion(),w.paymentId()));}
 public void finish(Work w,Channel c){tx.executeWithoutResult(s->{if(!fence(w))return;var p=payment(w.actor(),w.paymentId());if(c==null||!c.paymentId().equals(p.paymentId())||!c.attemptId().equals(w.attemptId())||!c.amount().equals(p.amount())||!c.currency().equals("CNY")||!Set.of("OPEN","FAILED","SUCCEEDED","CLOSED_UNPAID").contains(c.state()))throw new IllegalStateException("Channel observation mismatch");long now=now();
   one(db.update("UPDATE b_payment_attempt SET state=?,channel_transaction_id=?,paid_at_ms=?,version=version+1,last_error=NULL,updated_at_ms=? WHERE payment_id=? AND attempt_id=?",c.state(),c.channelTransactionId(),c.paidAt(),now,w.paymentId(),w.attemptId()));
   // .2 stores a channel observation, never the final market success without the .3 transactional outbox.
   one(db.update("UPDATE b_payment SET funds_state=?,version=version+1,last_error=?,updated_at_ms=? WHERE payment_id=?",p.fundsState().equals("SUCCEEDED")?"SUCCEEDED":c.state().equals("SUCCEEDED")?"UNKNOWN":"UNPAID",p.fundsState().equals("SUCCEEDED")?p.errorCode():c.state().equals("SUCCEEDED")?"PAYMENT_SYNC_PENDING":null,now,w.paymentId()));
   db.update("UPDATE b_payment_operation SET progress='APPLIED' WHERE payment_id=? AND attempt_id=? AND progress IN ('PENDING','WAITING_DEPENDENCY')",w.paymentId(),w.attemptId());
   one(db.update("UPDATE b_payment_task SET state='DONE',lease_token=NULL,lease_until_ms=NULL,last_error=NULL WHERE payment_id=?",w.paymentId()));
  });}
 public void retry(Work w,String code){tx.executeWithoutResult(s->{if(!fence(w))return;long now=now();one(db.update("UPDATE b_payment_task SET state='WAITING_DEPENDENCY',next_attempt_ms=?,failure_count=failure_count+1,last_error=?,lease_token=NULL,lease_until_ms=NULL WHERE payment_id=?",now+3000,code,w.paymentId()));db.update("UPDATE b_payment_operation SET progress='WAITING_DEPENDENCY' WHERE payment_id=? AND attempt_id=? AND progress='PENDING'",w.paymentId(),w.attemptId());db.update("UPDATE b_payment SET last_error=?,version=version+1,updated_at_ms=? WHERE payment_id=?",code,now,w.paymentId());});}
 private String encode(Object v){try{return json.writeValueAsString(v);}catch(Exception e){throw new IllegalStateException("Payment serialization failed",e);}}
 private <T>T decode(String v,Class<T> type){try{return json.readValue(v,type);}catch(Exception e){throw new IllegalStateException("Payment serialization invalid",e);}}
 private static void one(int n){if(n!=1)throw new IllegalStateException("Payment atomic write mismatch");}
}
