package cn.zj.zjmarket.infrastructure.gateway.mq;
import cn.zj.zjmarket.domain.payment.adapter.repository.ISettlementRepository;
import cn.zj.zjmarket.domain.payment.model.valobj.*;
import cn.zj.zjmarket.domain.product.model.valobj.SyncBadMessage;
import cn.zj.zjmarket.infrastructure.config.properties.MqSettings;
import cn.zj.zjmarket.infrastructure.gateway.codec.ContractCodec;
import cn.zj.zjmarket.types.exception.SyncTransportFailure;
import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.core.JsonParser;
import java.nio.charset.StandardCharsets;
import java.util.*;
import static cn.zj.zjmarket.infrastructure.gateway.mq.SyncResultReader.*;
public final class TradeMessageReader {
 private final MqSettings settings;private final ISettlementRepository repo;private final Map<String,String> keys;
 private final ObjectMapper json=new ObjectMapper().enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION).enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS);
 public TradeMessageReader(MqSettings settings,ISettlementRepository repo,Map<String,String> keys){this.settings=settings;this.repo=repo;this.keys=Map.copyOf(keys);}
 public void receive(SyncBadMessage m){receive(m,null,null,null,false);}
 public void receive(SyncBadMessage m,String key,String source,String channel){receive(m,key,source,channel,true);}
 private void receive(SyncBadMessage m,String key,String source,String channel,boolean metadata){try{var result=decode(m);if(metadata){var e=json.readTree(m.body());if(!Objects.equals(key,e.path("eventId").asText())||!settings.getSource().equals(source)||!settings.getChannel().equals(channel))throw bad("MESSAGE_METADATA_INVALID");}if(result!=null)repo.receive(result);}catch(SyncTransportFailure invalid){repo.quarantine(UUID.randomUUID().toString(),m.topic(),m.tag(),m.keyId(),m.signature(),m.body(),invalid.code());}catch(java.io.IOException invalid){repo.quarantine(UUID.randomUUID().toString(),m.topic(),m.tag(),m.keyId(),m.signature(),m.body(),"TRADE_STRUCTURE_INVALID");}}
 public TradeReceipt decode(SyncBadMessage m){try{
  if(m.body()==null||m.body().length>256*1024)throw bad("BODY_TOO_LARGE");
  boolean result=settings.getResultTopic().equals(m.topic())&&"EVENT_PROCESSING_RESULT".equals(m.tag());
  boolean team=settings.getTeamTopic().equals(m.topic())&&Set.of("TEAM_COMPLETED","TEAM_FAILED","TEAM_RECONCILIATION_REQUIRED").contains(m.tag());
  if(!result&&!team)throw bad("UNEXPECTED_TOPIC_OR_TAG");
  String secret=keys.get(m.keyId());if(secret==null||!ContractCodec.validSignature(secret,m.topic(),m.body(),m.signature()))throw bad("SIGNATURE_INVALID");
  var e=json.readTree(m.body());fields(e,"eventId,eventType,schemaVersion,producer,occurredAt,source,channel,correlationId,payload");
  String event=id(e,"eventId",64);if(!m.tag().equals(text(e,"eventType"))||!e.path("schemaVersion").isIntegralNumber()||!e.path("schemaVersion").bigIntegerValue().equals(java.math.BigInteger.ONE))throw bad("SCHEMA_INVALID");
  if(!settings.getAProducerId().equals(text(e,"producer"))||!settings.getSource().equals(text(e,"source"))||!settings.getChannel().equals(text(e,"channel")))throw bad("SOURCE_INVALID");
  utc(e,"occurredAt");if(!e.get("correlationId").isNull())id(e,"correlationId",64);
  var p=e.get("payload");String original=null;
  if(result){validateResult(p);original=id(p,"originalEventId",64);if(!e.get("correlationId").isNull()&&!original.equals(text(e,"correlationId")))throw bad("CORRELATION_INVALID");if(!Set.of("PAYMENT_SUCCEEDED","REFUND_STATUS_CHANGED").contains(text(p,"originalEventType")))return null;}
  else validateTeam(m.tag(),p);
  return new TradeReceipt(settings.getAProducerId(),event,m.tag(),ContractCodec.sha256(m.body()),new String(m.body(),StandardCharsets.UTF_8),original);
 }catch(SyncTransportFailure e){throw e;}catch(Exception e){throw bad("TRADE_STRUCTURE_INVALID");}}
 public static void validateResult(JsonNode p){
  fields(p,"originalEventId,originalEventType,outcome,code,info,processedAt,result");id(p,"originalEventId",64);String type=text(p,"originalEventType");if(!Set.of("PRODUCT_SNAPSHOT_CHANGED","PAYMENT_SUCCEEDED","REFUND_STATUS_CHANGED").contains(type))throw bad("UNSUPPORTED_ORIGINAL_TYPE");
  String outcome=text(p,"outcome"),code=id(p,"code",64);text(p,"info");utc(p,"processedAt");
  if(outcome.equals("REJECTED")){if(code.equals("0000")||!p.get("result").isNull())throw bad("RESULT_STRUCTURE_INVALID");return;}
  if(!Set.of("APPLIED","IGNORED").contains(outcome)||!code.equals("0000")||!p.path("result").isObject())throw bad("RESULT_STRUCTURE_INVALID");
  if(type.equals("PAYMENT_SUCCEEDED"))validatePaymentResult(p.get("result"));if(type.equals("REFUND_STATUS_CHANGED"))validateRefundResult(p.get("result"));
 }
 public static void validateRefundResult(JsonNode p){fields(p,"outTradeNo,refundId,refundStatus,refundVersion,recordVersion");id(p,"outTradeNo",64);id(p,"refundId",64);version(p,"refundVersion");version(p,"recordVersion");if(!Set.of("PENDING","FAILED","SUCCEEDED").contains(text(p,"refundStatus")))throw bad("RESULT_STRUCTURE_INVALID");}
 public static void validatePaymentResult(JsonNode p){fields(p,"orderId,outTradeNo,teamId,payment,orderStatus,teamStatus,recordVersion,teamVersion");for(String k:List.of("orderId","outTradeNo","teamId"))id(p,k,64);version(p,"recordVersion");version(p,"teamVersion");if(!"PAID".equals(text(p,"orderStatus"))||!Set.of("FORMING","RECONCILING","COMPLETED","FAILED").contains(text(p,"teamStatus")))throw bad("RESULT_STRUCTURE_INVALID");
  var pay=p.get("payment");fields(pay,"paymentId,paidAmount,currency,paidAt");id(pay,"paymentId",64);String amount=text(pay,"paidAmount");if(!amount.matches("(?:0|[1-9][0-9]{0,5})\\.[0-9]{2}")||new java.math.BigDecimal(amount).signum()<=0||!"CNY".equals(text(pay,"currency")))throw bad("RESULT_STRUCTURE_INVALID");utc(pay,"paidAt");}
 private static void version(JsonNode p,String k){cn.zj.zjmarket.domain.order.model.valobj.ReservationEvidence.version(text(p,k));}
 public static List<String> roster(JsonNode p,String k){var list=p.get(k);if(list==null||!list.isArray()||list.size()>100)throw bad("ROSTER_INVALID");var all=new ArrayList<String>();for(var item:list){if(!item.isTextual()||item.textValue().isBlank()||item.textValue().length()>64||!item.textValue().equals(item.textValue().trim())||all.contains(item.textValue()))throw bad("ROSTER_INVALID");all.add(item.textValue());}return all;}
 public static void validateTeam(String type,JsonNode p){String base="teamId,activityId,teamVersion,outTradeNoList";fields(p,base+(type.equals("TEAM_FAILED")?",reconciliationId,reason,refundRequiredOutTradeNoList":type.equals("TEAM_RECONCILIATION_REQUIRED")?",reconciliationId,rosterVersion,validEndTime":""));id(p,"teamId",64);version(p,"activityId");version(p,"teamVersion");var all=roster(p,"outTradeNoList");if(type.equals("TEAM_COMPLETED")&&all.isEmpty())throw bad("ROSTER_INVALID");if(!type.equals("TEAM_COMPLETED"))id(p,"reconciliationId",64);if(type.equals("TEAM_RECONCILIATION_REQUIRED")){version(p,"rosterVersion");utc(p,"validEndTime");}if(type.equals("TEAM_FAILED")){if(!"TARGET_NOT_REACHED".equals(text(p,"reason"))||!all.containsAll(roster(p,"refundRequiredOutTradeNoList")))throw bad("ROSTER_INVALID");}}
 private static SyncTransportFailure bad(String code){return new SyncTransportFailure(code,true);}
}
