package cn.zj.zjmarket.infrastructure.adapter.port.payment;

import cn.zj.zjmarket.domain.payment.adapter.port.ISimulatedChannel;
import cn.zj.zjmarket.domain.payment.model.valobj.*;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
import cn.zj.zjmarket.domain.order.service.impl.OrderService;
import cn.zj.zjmarket.types.exception.OrderFailure;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.*;
import org.springframework.transaction.support.*;
import javax.sql.DataSource;
import java.util.*;

/** Independent, durable simulator. No ambient market transaction may cross this port. */
public final class SimulatedChannel implements cn.zj.zjmarket.domain.payment.adapter.port.IChannelClosing,ISimulatedChannel,cn.zj.zjmarket.domain.payment.adapter.port.IChannelFacts {
 private final JdbcTemplate db;private final TransactionTemplate tx;private final ObjectMapper json=new ObjectMapper();
 public SimulatedChannel(DataSource source,TransactionTemplate tx){db=new JdbcTemplate(source);this.tx=tx;}
 private void outside(){if(TransactionSynchronizationManager.isActualTransactionActive())throw new IllegalStateException("Channel calls require an independent transaction");}
 private long now(){return db.queryForObject("SELECT CAST(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3))*1000 AS SIGNED)",Long.class);}
 private <T>T first(String sql,RowMapper<T> mapper,Object...args){var rows=db.query(sql,mapper,args);return rows.isEmpty()?null:rows.getFirst();}
 private Channel read(String payment,String attempt){return first("SELECT a.*,p.amount,p.currency FROM b_sim_attempt a JOIN b_sim_payment p ON p.payment_id=a.payment_id WHERE a.payment_id=? AND a.attempt_id=?",(rs,n)->{long paid=rs.getLong("paid_at_ms");Long paidAt=rs.wasNull()?null:paid;return new Channel(payment,attempt,rs.getString("state"),rs.getString("channel_transaction_id"),rs.getBigDecimal("amount").toPlainString(),rs.getString("currency"),paidAt);},payment,attempt);}
 public Channel query(String payment,String attempt){outside();return read(payment,attempt);}
 private Map<String,Object> root(String id){var rows=db.queryForList("SELECT * FROM b_sim_payment WHERE payment_id=? FOR UPDATE",id);return rows.isEmpty()?null:rows.getFirst();}
 private String parent(String id){return first("SELECT snapshot_hash FROM b_payment WHERE payment_id=? FOR SHARE",(rs,n)->rs.getString(1),id);}
 public Channel create(Payment p,Attempt a,MarketOrder order,Evidence evidence){outside();return tx.execute(status->{
  String frozenHash=parent(p.paymentId());if(frozenHash==null)throw new IllegalStateException("Missing committed payment");
  // Shared market parent before channel root is intentional: FK checks follow the same lock order.
  var root=root(p.paymentId());var old=read(p.paymentId(),a.attemptId());
  String requestHash=first("SELECT request_hash FROM b_payment_attempt WHERE payment_id=? AND attempt_id=?",(rs,n)->rs.getString(1),p.paymentId(),a.attemptId());
  if(requestHash==null)throw new IllegalStateException("Missing committed attempt");
  if(old!=null){String original=first("SELECT request_hash FROM b_sim_attempt WHERE attempt_id=?",(rs,n)->rs.getString(1),a.attemptId());if(!original.equals(requestHash))throw new OrderFailure(409,"IDEMPOTENCY_CONFLICT");return old;}
  long now=now();evidence.validate(order,now);
  if(root==null){db.update("INSERT INTO b_sim_payment(payment_id,amount,reserved_at_ms,payment_deadline_ms,snapshot_hash,created_at_ms) VALUES(?,?,?,?,?,?)",p.paymentId(),p.amount(),cn.zj.zjmarket.domain.order.model.valobj.ReservationEvidence.instant(order.evidence().reservedAt()),p.paymentDeadline(),frozenHash,now);root=root(p.paymentId());}
  if(!frozenHash.equals(root.get("snapshot_hash"))||!p.amount().equals(root.get("amount").toString())||p.paymentDeadline()!=((Number)root.get("payment_deadline_ms")).longValue())throw new IllegalStateException("Channel frozen terms mismatch");
  String gate=root.get("gate").toString();if(gate.equals("PAID"))throw new OrderFailure(409,"PAYMENT_ALREADY_PAID");
  var last=first("SELECT state FROM b_sim_attempt WHERE payment_id=? ORDER BY attempt_no DESC LIMIT 1 FOR UPDATE",(rs,n)->rs.getString(1),p.paymentId());
  if(last!=null&&!last.equals("FAILED")&&!gate.equals("CLOSED_UNPAID"))throw new OrderFailure(409,"PAYMENT_ATTEMPT_ACTIVE");
  String state=gate.equals("CLOSED_UNPAID")?"CLOSED_UNPAID":"OPEN";
  db.update("INSERT INTO b_sim_attempt(attempt_id,payment_id,attempt_no,channel_transaction_id,state,request_hash,created_at_ms) VALUES(?,?,?,?,?,?,?)",a.attemptId(),p.paymentId(),a.attemptNo(),UUID.randomUUID().toString(),state,requestHash,now);
  var result=read(p.paymentId(),a.attemptId());saveOperation(result,"CREATE_ATTEMPT",requestHash,now);return result;
 });}
 public Channel choose(Payment p,Attempt a,MarketOrder order,Evidence evidence,String result){outside();if(!Set.of("SUCCEEDED","FAILED").contains(result))throw new OrderFailure(400,"VALIDATION_FAILED");return tx.execute(status->{
  parent(p.paymentId());var root=root(p.paymentId());db.queryForList("SELECT attempt_id FROM b_sim_attempt WHERE payment_id=? ORDER BY attempt_no FOR UPDATE",p.paymentId());var original=read(p.paymentId(),a.attemptId());if(original==null||root==null)throw new OrderFailure(503,"PAYMENT_CHANNEL_NOT_FOUND");
  if(!original.state().equals("OPEN")){if(original.state().equals(result))return original;throw new OrderFailure(409,"PAYMENT_RESULT_CONFLICT");}
  if(!root.get("gate").equals("OPEN"))throw new OrderFailure(409,"PAYMENT_NOT_ALLOWED");
  long now=now();evidence.validate(order,now);
  if(!p.amount().equals(root.get("amount").toString())||p.paymentDeadline()!=((Number)root.get("payment_deadline_ms")).longValue())throw new IllegalStateException("Channel frozen terms mismatch");
  db.update("UPDATE b_sim_attempt SET state=?,paid_at_ms=? WHERE payment_id=? AND attempt_id=? AND state='OPEN'",result,result.equals("SUCCEEDED")?now:null,p.paymentId(),a.attemptId());
  if(result.equals("SUCCEEDED"))db.update("UPDATE b_sim_payment SET gate='PAID',success_attempt_id=?,version=version+1 WHERE payment_id=? AND gate='OPEN'",a.attemptId(),p.paymentId());
  var fact=read(p.paymentId(),a.attemptId());saveOperation(fact,"CHOOSE_RESULT",OrderService.hash(result),now);
  String body=encode(fact);db.update("INSERT INTO b_sim_notification(notification_id,payment_id,attempt_id,fact_json,fact_hash,next_attempt_ms,created_at_ms) VALUES(?,?,?,?,?,?,?)",UUID.randomUUID().toString(),p.paymentId(),a.attemptId(),body,OrderService.hash(body),now,now);
  return fact;
 });}

 public ChannelFact fact(String payment,String attempt){outside();return first("SELECT a.*,p.amount,p.currency,p.snapshot_hash,p.gate,p.success_attempt_id,p.reserved_at_ms,p.payment_deadline_ms FROM b_sim_attempt a JOIN b_sim_payment p ON p.payment_id=a.payment_id WHERE a.payment_id=? AND a.attempt_id=?",(rs,n)->{long paid=rs.getLong("paid_at_ms");Long t=rs.wasNull()?null:paid;return new ChannelFact(new Channel(payment,attempt,rs.getString("state"),rs.getString("channel_transaction_id"),rs.getBigDecimal("amount").toPlainString(),rs.getString("currency"),t),rs.getString("snapshot_hash"),rs.getString("request_hash"),rs.getString("gate"),rs.getString("success_attempt_id"),rs.getLong("reserved_at_ms"),rs.getLong("payment_deadline_ms"));},payment,attempt);}
 public List<ChannelNotice> notices(int size){outside();return tx.execute(s->{long now=now();var rows=db.queryForList("SELECT * FROM b_sim_notification WHERE state IN ('READY','LEASED') AND next_attempt_ms<=? AND (lease_until_ms IS NULL OR lease_until_ms<=?) ORDER BY next_attempt_ms,notification_id LIMIT ? FOR UPDATE SKIP LOCKED",now,now,size);var all=new ArrayList<ChannelNotice>();for(var row:rows){String token=UUID.randomUUID().toString();db.update("UPDATE b_sim_notification SET state='LEASED',lease_token=?,lease_until_ms=?,next_attempt_ms=?,failure_count=failure_count+1 WHERE notification_id=?",token,now+30000,now+30000,row.get("notification_id"));try{String body=encode(json.readValue(row.get("fact_json").toString(),Channel.class));all.add(new ChannelNotice(row.get("notification_id").toString(),row.get("payment_id").toString(),row.get("attempt_id").toString(),body,row.get("fact_hash").toString(),token,json.readValue(row.get("fact_json").toString(),Channel.class),Math.addExact(((Number)row.get("failure_count")).intValue(),1)));}catch(Exception invalid){db.update("UPDATE b_sim_notification SET state='REVIEW_REQUIRED',lease_token=NULL,lease_until_ms=NULL WHERE notification_id=? AND lease_token=?",row.get("notification_id"),token);}}return all;});}
 public void retry(ChannelNotice n){outside();long delay=Math.min(30000L,2000L*(1L<<Math.min(4,Math.max(0,n.failures()-1))))+java.util.concurrent.ThreadLocalRandom.current().nextLong(251);tx.executeWithoutResult(s->{Long now=noticeTime(n);if(now==null)return;db.update("UPDATE b_sim_notification SET state='READY',next_attempt_ms=?,lease_token=NULL,lease_until_ms=NULL WHERE notification_id=? AND state='LEASED' AND lease_token=? AND lease_until_ms>?",now+delay,n.id(),n.token(),now);});}
 public void acknowledge(ChannelNotice n,boolean review){outside();tx.executeWithoutResult(s->{Long now=noticeTime(n);if(now==null)return;db.update("UPDATE b_sim_notification SET state=?,lease_token=NULL,lease_until_ms=NULL WHERE notification_id=? AND state='LEASED' AND lease_token=? AND lease_until_ms>?",review?"REVIEW_REQUIRED":"DONE",n.id(),n.token(),now);});}
 // The database timestamp must be read in a separate statement after acquiring this row lock.
 private Long noticeTime(ChannelNotice notice){
  var rows=db.queryForList("SELECT state,lease_token,lease_until_ms FROM b_sim_notification WHERE notification_id=? FOR UPDATE",notice.id());
  if(rows.isEmpty())return null;
  var row=rows.getFirst();long current=now();
  if(!"LEASED".equals(row.get("state"))||!Objects.equals(notice.token(),row.get("lease_token"))||row.get("lease_until_ms")==null||((Number)row.get("lease_until_ms")).longValue()<=current)return null;
  return current;
 }
 public ChannelClosure queryClose(PaymentClose request){outside();return tx.execute(s->{parent(request.paymentId());var r=root(request.paymentId());return r==null?null:storedClose(r,request);});}
 private ChannelClosure storedClose(Map<String,Object> root,PaymentClose request){
  if(root.get("close_id")==null)return null;
  if(!request.closeId().equals(root.get("close_id"))||!OrderService.hash(encode(request)).equals(root.get("close_request_hash")))throw new OrderFailure(409,"CHANNEL_CLOSE_CONFLICT");
  try{String raw=new String((byte[])root.get("close_result"),java.nio.charset.StandardCharsets.UTF_8);if(!OrderService.hash(raw).equals(root.get("close_result_hash")))throw new IllegalArgumentException("Root close hash mismatch");var result=json.readValue(raw,ChannelClosure.class);if(!request.equals(result.request())||!result.gate().equals(root.get("gate")))throw new IllegalArgumentException("Root close state conflict");
   if("CLOSED_UNPAID".equals(result.gate())){var current=db.query("SELECT * FROM b_sim_attempt WHERE payment_id=? ORDER BY attempt_no",(rs,i)->new ClosedAttempt(rs.getString("attempt_id"),rs.getInt("attempt_no"),rs.getString("request_hash"),rs.getString("channel_transaction_id"),rs.getString("state")),request.paymentId());if(!result.closedAt().equals(((Number)root.get("closed_at_ms")).longValue())||!result.attempts().equals(current))throw new IllegalArgumentException("Root close attempt conflict");}
   else if(!"PAID".equals(result.gate())||!Objects.equals(result.paid(),factInside(request.paymentId(),root.get("success_attempt_id").toString())))throw new IllegalArgumentException("Root paid fact conflict");return result;}catch(java.io.IOException e){throw new IllegalArgumentException("Root close invalid",e);}
 }
 public ChannelClosure closeRoot(PaymentClose request){outside();return tx.execute(s->{
  String frozen=parent(request.paymentId());if(!request.snapshotHash().equals(frozen))throw new IllegalArgumentException("Root parent mismatch");
  var r=root(request.paymentId());long n=now();
  if(r==null){db.update("INSERT INTO b_sim_payment(payment_id,amount,reserved_at_ms,payment_deadline_ms,snapshot_hash,created_at_ms) VALUES(?,?,?,?,?,?)",request.paymentId(),request.amount(),request.reservedAt(),request.deadline(),request.snapshotHash(),n);r=root(request.paymentId());}
  var saved=storedClose(r,request);if(saved!=null)return saved;
  if(!request.snapshotHash().equals(r.get("snapshot_hash"))||!request.amount().equals(r.get("amount").toString())||!request.currency().equals(r.get("currency"))||request.reservedAt()!=((Number)r.get("reserved_at_ms")).longValue()||request.deadline()!=((Number)r.get("payment_deadline_ms")).longValue())throw new IllegalArgumentException("Root terms mismatch");
  db.queryForList("SELECT attempt_id FROM b_sim_attempt WHERE payment_id=? ORDER BY attempt_no FOR UPDATE",request.paymentId());
  ChannelClosure result;
  if("PAID".equals(r.get("gate"))){result=new ChannelClosure(request,"PAID",null,List.of(),factInside(request.paymentId(),r.get("success_attempt_id").toString()));}
  else{
   for(var a:request.attempts()){
    String committed=first("SELECT request_hash FROM b_payment_attempt WHERE payment_id=? AND attempt_id=? AND attempt_no=?",(rs,i)->rs.getString(1),request.paymentId(),a.attemptId(),a.attemptNo());if(!a.requestHash().equals(committed))throw new IllegalArgumentException("Uncommitted close attempt");
    if(read(request.paymentId(),a.attemptId())==null)db.update("INSERT INTO b_sim_attempt(attempt_id,payment_id,attempt_no,channel_transaction_id,state,request_hash,created_at_ms) VALUES(?,?,?,?,'CLOSED_UNPAID',?,?)",a.attemptId(),request.paymentId(),a.attemptNo(),UUID.randomUUID().toString(),a.requestHash(),n);
   }
   db.update("UPDATE b_sim_attempt SET state='CLOSED_UNPAID' WHERE payment_id=? AND state='OPEN'",request.paymentId());
   db.update("UPDATE b_sim_payment SET gate='CLOSED_UNPAID',closed_at_ms=?,version=version+1 WHERE payment_id=? AND gate='OPEN'",n,request.paymentId());
   var all=db.query("SELECT * FROM b_sim_attempt WHERE payment_id=? ORDER BY attempt_no",(rs,i)->new ClosedAttempt(rs.getString("attempt_id"),rs.getInt("attempt_no"),rs.getString("request_hash"),rs.getString("channel_transaction_id"),rs.getString("state")),request.paymentId());
   long closed=((Number)root(request.paymentId()).get("closed_at_ms")).longValue();result=new ChannelClosure(request,"CLOSED_UNPAID",closed,all,null);result.validateUnpaid(request,n);
  }
  String raw=encode(result);db.update("UPDATE b_sim_payment SET close_id=?,close_request_hash=?,close_result=?,close_result_hash=? WHERE payment_id=?",request.closeId(),OrderService.hash(encode(request)),raw.getBytes(java.nio.charset.StandardCharsets.UTF_8),OrderService.hash(raw),request.paymentId());return result;
 });}
 private ChannelFact factInside(String payment,String attempt){return first("SELECT a.*,p.amount,p.currency,p.snapshot_hash,p.gate,p.success_attempt_id,p.reserved_at_ms,p.payment_deadline_ms FROM b_sim_attempt a JOIN b_sim_payment p ON p.payment_id=a.payment_id WHERE a.payment_id=? AND a.attempt_id=?",(rs,i)->new ChannelFact(new Channel(payment,attempt,rs.getString("state"),rs.getString("channel_transaction_id"),rs.getBigDecimal("amount").toPlainString(),rs.getString("currency"),rs.getLong("paid_at_ms")),rs.getString("snapshot_hash"),rs.getString("request_hash"),rs.getString("gate"),rs.getString("success_attempt_id"),rs.getLong("reserved_at_ms"),rs.getLong("payment_deadline_ms")),payment,attempt);}
 private void saveOperation(Channel c,String action,String hash,long now){db.update("INSERT INTO b_sim_operation(payment_id,attempt_id,action,request_hash,result_json,created_at_ms) VALUES(?,?,?,?,?,?)",c.paymentId(),c.attemptId(),action,hash,encode(c),now);}
 private String encode(Object value){try{return json.writeValueAsString(value);}catch(Exception e){throw new IllegalStateException("Channel serialization failed",e);}}
}
