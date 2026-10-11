package cn.zj.zjmarket.infrastructure.adapter.repository;
import cn.zj.zjmarket.infrastructure.gateway.codec.ContractCodec;
import cn.zj.zjmarket.domain.refund.model.Refund;
import com.fasterxml.jackson.databind.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import java.util.*;
import java.nio.charset.StandardCharsets;

/** Called inside the original order/refund transaction; channel facts are never reconstructed. */
public final class RefundOutbox {
 private final JdbcTemplate db;private final String producer,source,channel;private final ObjectMapper json=new ObjectMapper();
 public RefundOutbox(JdbcTemplate db,String producer,String source,String channel){this.db=db;this.producer=producer;this.source=source;this.channel=channel;}
 public void validateSchema(){db.queryForList("SELECT refund_id FROM b_trade_outbox LIMIT 0");db.queryForList("SELECT sync_status,accepted_version FROM b_refund LIMIT 0");db.queryForList("SELECT authority_hash FROM b_trade_inbox LIMIT 0");}
 public static String eventId(String id,long version){return hash(("refund|"+id+"|"+version).getBytes(StandardCharsets.UTF_8));}
 private static String hash(byte[] raw){try{return ContractCodec.sha256(raw);}catch(Exception e){throw new IllegalArgumentException(e);}}
 private byte[] encode(Object value){try{return new ContractCodec().encode(value);}catch(Exception e){throw new IllegalArgumentException(e);}}
 public void materialize(String id){Refund.require(TransactionSynchronizationManager.isActualTransactionActive());var f=db.queryForMap("SELECT * FROM b_refund WHERE refund_id=?",id);
  var scope=db.queryForMap("SELECT a_evidence FROM b_market_order WHERE order_id=?",f.get("order_id"));try{var a=json.readTree(scope.get("a_evidence").toString());Refund.require(source.equals(a.path("source").asText())&&channel.equals(a.path("channel").asText()));}catch(java.io.IOException e){throw new IllegalArgumentException(e);}
  for(var attempt:db.queryForList("SELECT * FROM b_refund_attempt WHERE refund_id=? ORDER BY attempt_no",id)){one(f,attempt,"pending");if(attempt.get("result_fact")!=null)one(f,attempt,"result");}
  db.update("UPDATE b_refund SET sync_status=IF(accepted_version=fact_version,'ACCEPTED','PENDING'),version=version+1,updated_at_ms=CAST(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3))*1000 AS SIGNED) WHERE refund_id=? AND fact_version>0 AND sync_status<>'REVIEW_REQUIRED' AND sync_status<>IF(accepted_version=fact_version,'ACCEPTED','PENDING')",id);
 }
 private void one(Map<String,Object> f,Map<String,Object> a,String kind){byte[] raw=(byte[])a.get(kind+"_fact");Refund.require(raw!=null&&hash(raw).equals(a.get(kind+"_hash")));long version=((Number)a.get(kind+"_version")).longValue();JsonNode fact;try{fact=json.readTree(raw);}catch(Exception e){throw new IllegalArgumentException(e);}
  Refund.require(version>0&&Long.toString(version).equals(fact.path("refundVersion").asText())&&f.get("refund_id").equals(fact.path("refundId").asText())&&f.get("payment_id").equals(fact.path("paymentId").asText())&&f.get("order_id").equals(fact.path("outTradeNo").asText())&&f.get("amount").toString().equals(fact.path("refundAmount").asText())&&"CNY".equals(fact.path("currency").asText()));
  String state=fact.path("refundStatus").asText();Refund.require(kind.equals("pending")?state.equals("PENDING"):Set.of("FAILED","SUCCEEDED").contains(state));
  var payload=new TreeMap<String,Object>();for(String k:List.of("refundId","paymentId","outTradeNo","refundAmount","currency","refundStatus","refundVersion","occurredAt","paidAt","paidAmount"))payload.put(k,fact.path(k).asText());payload.put("userId",f.get("user_id"));
  String event=eventId(f.get("refund_id").toString(),version);var envelope=new TreeMap<String,Object>();envelope.put("eventId",event);envelope.put("eventType","REFUND_STATUS_CHANGED");envelope.put("schemaVersion",1);envelope.put("producer",producer);envelope.put("occurredAt",fact.path("occurredAt").asText());envelope.put("source",source);envelope.put("channel",channel);envelope.put("correlationId",f.get("order_id"));envelope.put("payload",payload);byte[] wire=encode(envelope);String digest=hash(wire);
  db.update("INSERT INTO b_trade_outbox(event_id,payment_id,order_id,refund_id,event_type,fact_version,body,body_hash,next_attempt_ms,created_at_ms) VALUES(?,?,?,?,'REFUND_STATUS_CHANGED',?,?,?,0,CAST(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3))*1000 AS SIGNED)) ON DUPLICATE KEY UPDATE event_id=event_id",event,f.get("payment_id"),f.get("order_id"),f.get("refund_id"),version,wire,digest);
  var old=db.queryForMap("SELECT * FROM b_trade_outbox WHERE payment_id=? AND event_type='REFUND_STATUS_CHANGED' AND fact_version=?",f.get("payment_id"),version);Refund.require(event.equals(old.get("event_id"))&&f.get("refund_id").equals(old.get("refund_id"))&&digest.equals(old.get("body_hash"))&&Arrays.equals(wire,(byte[])old.get("body")));
 }
}
