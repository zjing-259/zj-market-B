package cn.zj.zjmarket.infrastructure.adapter.port.refund;

import cn.zj.zjmarket.domain.refund.adapter.port.IRefundChannel;
import cn.zj.zjmarket.domain.refund.model.Refund;
import cn.zj.zjmarket.domain.refund.model.Refund.*;
import cn.zj.zjmarket.domain.payment.model.valobj.ChannelFact;
import cn.zj.zjmarket.infrastructure.gateway.codec.ContractCodec;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.support.*;
import javax.sql.DataSource;
import java.util.*;

/** Independent channel transactions. The payment root arbitrates the cumulative full refund. */
public final class SimulatedRefundChannel implements IRefundChannel {
 private final JdbcTemplate db;private final TransactionTemplate tx;private final Settings settings;private final ObjectMapper json=new ObjectMapper();
 public SimulatedRefundChannel(DataSource ds,TransactionTemplate tx,Settings settings){db=new JdbcTemplate(ds);this.tx=tx;this.settings=settings;}
 private void outside(){if(TransactionSynchronizationManager.isActualTransactionActive())throw new IllegalStateException("Refund channel requires an independent transaction");}
 private String digest(byte[] raw){try{return ContractCodec.sha256(raw);}catch(Exception e){throw new IllegalArgumentException(e);}}
 private long now(){return db.queryForObject("SELECT CAST(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3))*1000 AS SIGNED)",Long.class);}
 private Map<String,Object> first(String sql,Object...args){var rows=db.queryForList(sql,args);return rows.isEmpty()?null:rows.getFirst();}
 private byte[] bytes(Object value){try{return new ContractCodec().encode(value);}catch(Exception e){throw new IllegalArgumentException("Refund encoding failed",e);}}
 private <T>T decode(Map<String,Object> row,String field,Class<T> cls){byte[] raw=(byte[])row.get(field);Refund.require(raw!=null&&digest(raw).equals(row.get(field+"_hash")));try{return json.readValue(raw,cls);}catch(Exception e){throw new IllegalArgumentException("Refund channel stored fact invalid",e);}}
 private Fact stored(Request request){var row=first("SELECT * FROM b_sim_refund_attempt WHERE attempt_id=?",request.attemptId());if(row==null)return null;Refund.require(request.hash().equals(row.get("request_hash"))&&request.refundId().equals(row.get("refund_id")));var fact=decode(row,"fact",Fact.class);fact.validate(request,now());Refund.require(fact.status().equals(row.get("state")));return fact;}
 public Fact query(Request request){outside();return stored(request);}
 public Fact execute(Request request){outside();return tx.execute(s->{
  // No marketplace locks or callbacks; all channel competitors start at the original payment root.
  var payment=first("SELECT * FROM b_sim_payment WHERE payment_id=? FOR UPDATE",request.paymentId());Refund.require(payment!=null&&"PAID".equals(payment.get("gate"))&&request.paymentAttemptId().equals(payment.get("success_attempt_id"))&&request.amount().equals(payment.get("amount").toString())&&request.currency().equals(payment.get("currency"))&&request.paymentSnapshotHash().equals(payment.get("snapshot_hash")));
  var paid=first("SELECT * FROM b_sim_attempt WHERE payment_id=? AND attempt_id=?",request.paymentId(),request.paymentAttemptId());Refund.require(paid!=null&&"SUCCEEDED".equals(paid.get("state"))&&request.paymentTransactionId().equals(paid.get("channel_transaction_id"))&&request.paidAt()==((Number)paid.get("paid_at_ms")).longValue());
  var originalFact=new ChannelFact(new cn.zj.zjmarket.domain.payment.model.valobj.Channel(request.paymentId(),request.paymentAttemptId(),"SUCCEEDED",request.paymentTransactionId(),request.amount(),request.currency(),request.paidAt()),request.paymentSnapshotHash(),paid.get("request_hash").toString(),"PAID",request.paymentAttemptId(),((Number)payment.get("reserved_at_ms")).longValue(),((Number)payment.get("payment_deadline_ms")).longValue());
  // Preserve the exact canonical codec used by original payment M2.
  Refund.require(digest(bytes(originalFact)).equals(request.paymentSuccessHash()));
  var committed=first("SELECT request_hash FROM b_refund_attempt WHERE refund_id=? AND attempt_id=?",request.refundId(),request.attemptId());Refund.require(committed!=null&&request.hash().equals(committed.get("request_hash")));
  var root=first("SELECT * FROM b_sim_refund WHERE payment_id=? FOR UPDATE",request.paymentId());
  if(root==null){long n=now();byte[] raw=bytes(request);db.update("INSERT INTO b_sim_refund(refund_id,payment_id,amount,currency,root_request,root_hash,created_at_ms) VALUES(?,?,?,?,?,?,?)",request.refundId(),request.paymentId(),request.amount(),request.currency(),raw,digest(raw),n);root=first("SELECT * FROM b_sim_refund WHERE payment_id=? FOR UPDATE",request.paymentId());}
  Refund.require(request.refundId().equals(root.get("refund_id")));byte[] rootRaw=(byte[])root.get("root_request");Refund.require(digest(rootRaw).equals(root.get("root_hash")));try{Refund.require(request.sameRoot(json.readValue(rootRaw,Request.class)));}catch(java.io.IOException e){throw new IllegalArgumentException(e);}
  db.queryForList("SELECT attempt_id FROM b_sim_refund_attempt WHERE refund_id=? ORDER BY attempt_no FOR UPDATE",request.refundId());var old=stored(request);if(old!=null)return old;
  Refund.require(root.get("success_attempt_id")==null&&new java.math.BigDecimal(root.get("refunded_amount").toString()).signum()==0);
  var previous=first("SELECT state,attempt_no FROM b_sim_refund_attempt WHERE refund_id=? ORDER BY attempt_no DESC LIMIT 1",request.refundId());Refund.require(previous==null?request.attemptNo()==1:"FAILED".equals(previous.get("state"))&&request.attemptNo()==((Number)previous.get("attempt_no")).intValue()+1);
  long n=now();var fact=new Fact(request,"SUCCEEDED",UUID.randomUUID().toString(),n,1);fact.validate(request,n);byte[] raw=bytes(fact),req=bytes(request);
  db.update("INSERT INTO b_sim_refund_attempt(attempt_id,refund_id,attempt_no,request,request_hash,state,fact,fact_hash) VALUES(?,?,?,?,?,'SUCCEEDED',?,?)",request.attemptId(),request.refundId(),request.attemptNo(),req,request.hash(),raw,digest(raw));
  db.update("UPDATE b_sim_refund SET refunded_amount=amount,success_attempt_id=? WHERE refund_id=? AND refunded_amount=0 AND success_attempt_id IS NULL",request.attemptId(),request.refundId());
  db.update("INSERT INTO b_sim_refund_notification(notification_id,refund_id,attempt_id,next_attempt_ms,created_at_ms) VALUES(?,?,?,?,?)",UUID.randomUUID().toString(),request.refundId(),request.attemptId(),n,n);return fact;
 });}
 public List<Notice> notices(int size){outside();return tx.execute(s->{long scan=now();var rows=db.queryForList("SELECT * FROM b_sim_refund_notification WHERE state IN ('READY','LEASED') AND next_attempt_ms<=? AND (lease_until_ms IS NULL OR lease_until_ms<=?) ORDER BY next_attempt_ms,notification_id LIMIT ? FOR UPDATE SKIP LOCKED",scan,scan,size);var result=new ArrayList<Notice>();long n=now();for(var row:rows){String token=UUID.randomUUID().toString();db.update("UPDATE b_sim_refund_notification SET state='LEASED',lease_token=?,lease_until_ms=? WHERE notification_id=?",token,n+settings.leaseMillis(),row.get("notification_id"));result.add(new Notice(row.get("notification_id").toString(),row.get("refund_id").toString(),row.get("attempt_id").toString(),token,((Number)row.get("failure_count")).intValue()));}return result;});}
 private Long lockedTime(Notice notice){var row=first("SELECT * FROM b_sim_refund_notification WHERE notification_id=? FOR UPDATE",notice.id());long n=now();if(row==null||!"LEASED".equals(row.get("state"))||!notice.token().equals(row.get("lease_token"))||row.get("lease_until_ms")==null||((Number)row.get("lease_until_ms")).longValue()<=n)return null;return n;}
 public boolean renew(Notice notice){outside();return Boolean.TRUE.equals(tx.execute(s->{Long n=lockedTime(notice);if(n==null)return false;db.update("UPDATE b_sim_refund_notification SET lease_until_ms=? WHERE notification_id=?",n+settings.leaseMillis(),notice.id());return true;}));}
 public void acknowledge(Notice notice,boolean review){outside();tx.executeWithoutResult(s->{if(lockedTime(notice)==null)return;db.update("UPDATE b_sim_refund_notification SET state=?,lease_token=NULL,lease_until_ms=NULL WHERE notification_id=?",review?"REVIEW_REQUIRED":"DONE",notice.id());});}
 public void retry(Notice notice){outside();tx.executeWithoutResult(s->{Long n=lockedTime(notice);if(n==null)return;int failures=notice.failures()+1;db.update("UPDATE b_sim_refund_notification SET state='READY',next_attempt_ms=?,failure_count=?,alerted=alerted OR ?>=5,lease_token=NULL,lease_until_ms=NULL WHERE notification_id=?",n+settings.delay(failures),failures,failures,notice.id());if(failures==5)afterCommit("Refund notification retries require attention; original fact retained");});}
 private void afterCommit(String text){TransactionSynchronizationManager.registerSynchronization(new org.springframework.transaction.support.TransactionSynchronization(){public void afterCommit(){System.getLogger(SimulatedRefundChannel.class.getName()).log(System.Logger.Level.WARNING,text);}});}
}
