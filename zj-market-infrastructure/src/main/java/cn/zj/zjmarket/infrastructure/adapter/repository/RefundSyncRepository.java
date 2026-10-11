package cn.zj.zjmarket.infrastructure.adapter.repository;
import cn.zj.zjmarket.domain.refund.model.Refund;
import cn.zj.zjmarket.domain.order.model.valobj.ReservationEvidence;
import cn.zj.zjmarket.infrastructure.gateway.codec.ContractCodec;
import cn.zj.zjmarket.infrastructure.gateway.mq.TradeMessageReader;
import cn.zj.zjmarket.infrastructure.adapter.port.order.DubboTradePort;
import cn.zj.zjmarket.domain.order.adapter.repository.IOrderRepository;
import cn.bugstack.api.v2.Reservation;
import com.fasterxml.jackson.databind.*;
import org.springframework.jdbc.core.JdbcTemplate;
import java.util.*;
import java.nio.charset.StandardCharsets;

/** Funds, payment acceptance and inventory are never mutated by an A refund receipt. */
public final class RefundSyncRepository {
 private final JdbcTemplate db;private final RefundRepository refunds;private final IOrderRepository orders;private final ObjectMapper json=new ObjectMapper();
 public RefundSyncRepository(JdbcTemplate db,RefundRepository refunds,IOrderRepository orders){this.db=db;this.refunds=refunds;this.orders=orders;}
 private Map<String,Object> first(String sql,Object...args){var rows=db.queryForList(sql,args);return rows.isEmpty()?null:rows.getFirst();}
 private static String hash(byte[] raw){try{return ContractCodec.sha256(raw);}catch(Exception e){throw new IllegalArgumentException(e);}}
 private JsonNode tree(byte[] raw){try{return json.readTree(raw);}catch(Exception e){throw new IllegalArgumentException(e);}}
 private JsonNode checked(Map<String,Object> row,String key,String digest){byte[] raw=(byte[])row.get(key);Refund.require(raw!=null&&hash(raw).equals(row.get(digest)));return tree(raw);}
 public void apply(String id){var before=first("SELECT x.refund_id FROM b_trade_inbox i JOIN b_trade_outbox x ON x.event_id=i.original_event_id WHERE i.inbox_id=? AND x.event_type='REFUND_STATUS_CHANGED'",id);if(before==null)return;
  refunds.withLocked(before.get("refund_id").toString(),()->{var inbox=first("SELECT * FROM b_trade_inbox WHERE inbox_id=? FOR UPDATE",id);if(inbox==null||!Set.of("READY","WAITING_DEPENDENCY").contains(inbox.get("state")))return;var out=first("SELECT * FROM b_trade_outbox WHERE event_id=?",inbox.get("original_event_id"));var f=first("SELECT * FROM b_refund WHERE refund_id=?",before.get("refund_id"));String error=null;boolean wait=false;long accepted=0,record=0;String status=null;
   try{var event=checked(inbox,"body","body_hash");var envelope=checked(out,"body","body_hash");var payload=event.path("payload");TradeMessageReader.validateResult(payload);Refund.require(payload.path("originalEventType").asText().equals("REFUND_STATUS_CHANGED")&&out.get("event_id").equals(payload.path("originalEventId").asText()));var original=envelope.path("payload");Refund.require(f.get("refund_id").equals(original.path("refundId").asText())&&f.get("payment_id").equals(original.path("paymentId").asText())&&f.get("order_id").equals(original.path("outTradeNo").asText())&&f.get("user_id").equals(original.path("userId").asText())&&f.get("amount").toString().equals(original.path("refundAmount").asText())&&"CNY".equals(original.path("currency").asText()));
    if(payload.path("outcome").asText().equals("REJECTED"))error="A_REFUND_REJECTED";
    else{var result=payload.path("result");TradeMessageReader.validateRefundResult(result);Refund.require(f.get("refund_id").equals(result.path("refundId").asText())&&f.get("order_id").equals(result.path("outTradeNo").asText()));accepted=ReservationEvidence.version(result.path("refundVersion").asText());record=ReservationEvidence.version(result.path("recordVersion").asText());status=result.path("refundStatus").asText();long sent=((Number)out.get("fact_version")).longValue();Refund.require(accepted>=sent);
     var known=first("SELECT * FROM b_trade_outbox WHERE refund_id=? AND fact_version=? AND event_type='REFUND_STATUS_CHANGED'",f.get("refund_id"),accepted);Refund.require(known!=null);var knownFact=checked(known,"body","body_hash").path("payload");Refund.require(status.equals(knownFact.path("refundStatus").asText()));
     if(accepted>sent&&inbox.get("authority")==null)wait=true;
     if(inbox.get("authority")!=null){var snapshot=checked(inbox,"authority","authority_hash");Reservation a=json.treeToValue(snapshot,Reservation.class);var order=orders.byId(f.get("user_id").toString(),f.get("order_id").toString());DubboTradePort.map(a).validate(order);var ar=a.getRefund();Refund.require("FAILED".equals(a.getTeamStatus())&&f.get("team_id").equals(a.getTeamId()));Refund.require(ar!=null&&ar.getRefundId().equals(f.get("refund_id"))&&ar.getRefundAmount().equals(f.get("amount").toString())&&"CNY".equals(ar.getCurrency())&&ar.getRefundStatus().equals(status)&&ar.getRefundVersion().equals(Long.toString(accepted))&&ReservationEvidence.version(a.getRecordVersion())>=record);record=ReservationEvidence.version(a.getRecordVersion());
      if(a.getPayment()!=null){var p=first("SELECT * FROM b_payment WHERE payment_id=?",f.get("payment_id"));Refund.require(a.getPayment().getPaymentId().equals(f.get("payment_id"))&&a.getPayment().getPaidAmount().equals(f.get("amount").toString())&&"CNY".equals(a.getPayment().getCurrency())&&ReservationEvidence.instant(a.getPayment().getPaidAt())==((Number)p.get("paid_at_ms")).longValue());}else Refund.require("OUTSIDE_WINDOW_RESOLVED".equals(f.get("eligibility_basis"))&&"CANCELLED".equals(a.getOrderStatus()));
     }
     long high=((Number)f.get("accepted_version")).longValue();Refund.require(accepted!=high||high==0||status.equals(f.get("accepted_status")));Refund.require(!"SUCCEEDED".equals(f.get("accepted_status"))||accepted<=high||"SUCCEEDED".equals(status));
    }
   }catch(Exception invalid){error="A_REFUND_FACT_CONFLICT";}
   if(error!=null){byte[] raw=(byte[])inbox.get("body");db.update("INSERT INTO b_trade_quarantine(quarantine_id,receipt_key,topic,tag,body,body_hash,reason,created_at_ms) VALUES(?,?,'TRADE','REFUND_RESULT',?,?,?,CAST(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3))*1000 AS SIGNED)) ON DUPLICATE KEY UPDATE quarantine_id=quarantine_id",UUID.randomUUID().toString(),inbox.get("event_id"),raw,hash(raw),error);db.update("UPDATE b_refund SET sync_status='REVIEW_REQUIRED',sync_error=?,version=version+1,updated_at_ms=CAST(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3))*1000 AS SIGNED) WHERE refund_id=?",error,f.get("refund_id"));}
   else if(wait){db.update("UPDATE b_refund SET sync_status='WAITING_DEPENDENCY',sync_error='A_REFUND_QUERY_REQUIRED',version=version+1,updated_at_ms=CAST(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3))*1000 AS SIGNED) WHERE refund_id=? AND accepted_version<fact_version AND sync_status NOT IN ('REVIEW_REQUIRED','WAITING_DEPENDENCY')",f.get("refund_id"));}
   else{long high=((Number)f.get("accepted_version")).longValue();if(accepted>high)db.update("UPDATE b_refund SET accepted_version=?,accepted_status=?,a_record_version=GREATEST(a_record_version,?),sync_status=IF(sync_status='REVIEW_REQUIRED',sync_status,IF(fact_version=?,'ACCEPTED','PENDING')),sync_error=IF(sync_status='REVIEW_REQUIRED',sync_error,NULL),version=version+1,updated_at_ms=CAST(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3))*1000 AS SIGNED) WHERE refund_id=?",accepted,status,record,accepted,f.get("refund_id"));else if(record>((Number)f.get("a_record_version")).longValue())db.update("UPDATE b_refund SET a_record_version=?,version=version+1,updated_at_ms=CAST(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3))*1000 AS SIGNED) WHERE refund_id=?",record,f.get("refund_id"));}
   db.update("UPDATE b_trade_inbox SET state=?,last_error=?,next_attempt_ms=CAST(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3))*1000 AS SIGNED)+3000 WHERE inbox_id=?",error!=null?"REVIEW_REQUIRED":wait?"WAITING_DEPENDENCY":"DONE",error,id);
   if(!wait)db.update("UPDATE b_trade_outbox SET state=?,last_error=?,lease_token=NULL,lease_until_ms=NULL WHERE event_id=? AND (state<>'REVIEW_REQUIRED' OR ? IS NOT NULL)",error==null?"DONE":"REVIEW_REQUIRED",error,out.get("event_id"),error);
  });
 }
}
