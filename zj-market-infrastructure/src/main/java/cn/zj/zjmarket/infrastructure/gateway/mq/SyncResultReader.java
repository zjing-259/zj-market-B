package cn.zj.zjmarket.infrastructure.gateway.mq;

import cn.zj.zjmarket.domain.product.adapter.repository.IProductSyncRepository;
import cn.zj.zjmarket.domain.product.model.entity.Product;
import cn.zj.zjmarket.domain.product.model.valobj.SyncBadMessage;
import cn.zj.zjmarket.domain.product.model.valobj.SyncResult;
import cn.zj.zjmarket.infrastructure.config.properties.MqSettings;
import cn.zj.zjmarket.infrastructure.gateway.codec.ContractCodec;
import cn.zj.zjmarket.types.exception.ProductFailure;
import cn.zj.zjmarket.types.exception.SyncTransportFailure;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.*;
import java.time.Instant;
import java.util.*;
/** Verify original bytes before strict decoding; bounded quarantine ACK occurs only after persistence. */
public final class SyncResultReader {
 private final MqSettings settings;private final IProductSyncRepository store;private final Map<String,String> keys;
 private final ObjectMapper json=new ObjectMapper().enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION).enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS);
 public SyncResultReader(MqSettings settings,IProductSyncRepository store,Map<String,String> keys){this.settings=settings;this.store=store;this.keys=Map.copyOf(keys);}
 public boolean receive(SyncBadMessage message){
  try{var result=decode(message);if(result!=null)store.accept(result,"PRODUCT_SYNC_MQ");return true;}
  catch(SyncTransportFailure invalid){store.quarantine(new SyncBadMessage(message.topic(),message.tag(),message.keyId(),message.signature(),message.body(),invalid.code()));return false;}
 }
 public void replay(String id){var message=store.quarantinedBody(id);if(!receive(message))throw new ProductFailure(409,"RETRY_NOT_ALLOWED");store.replayed(id);}
 public SyncResult decode(SyncBadMessage message){
  try{
   if(message.body()==null || message.body().length>256*1024)throw invalid("BODY_TOO_LARGE");
   if(!settings.getResultTopic().equals(message.topic()) || !"EVENT_PROCESSING_RESULT".equals(message.tag()))throw invalid("UNEXPECTED_TOPIC_OR_TAG");
   String secret=keys.get(message.keyId());if(secret==null || !ContractCodec.validSignature(secret,message.topic(),message.body(),message.signature()))throw invalid("SIGNATURE_INVALID");
   var envelope=json.readTree(message.body());fields(envelope,"eventId,eventType,schemaVersion,producer,occurredAt,source,channel,correlationId,payload");
   String id=id(envelope,"eventId",64);if(!"EVENT_PROCESSING_RESULT".equals(text(envelope,"eventType")) || !envelope.path("schemaVersion").isIntegralNumber() || !envelope.path("schemaVersion").bigIntegerValue().equals(java.math.BigInteger.ONE))throw invalid("SCHEMA_INVALID");
   if(!settings.getAProducerId().equals(text(envelope,"producer")) || !settings.getSource().equals(text(envelope,"source")) || !settings.getChannel().equals(text(envelope,"channel")))throw invalid("SOURCE_INVALID");
   utc(envelope,"occurredAt");var payload=envelope.get("payload");
   TradeMessageReader.validateResult(payload);
   if(!envelope.get("correlationId").isNull()&&!id(payload,"originalEventId",64).equals(id(envelope,"correlationId",64)))throw invalid("CORRELATION_INVALID");
   if(!"PRODUCT_SNAPSHOT_CHANGED".equals(text(payload,"originalEventType")))return null;
   var result=parse(payload,id,settings.getAProducerId(),ContractCodec.sha256(message.body()));
   if(!envelope.get("correlationId").isNull() && !result.originalEventId().equals(id(envelope,"correlationId",64)))throw invalid("CORRELATION_INVALID");
   return result;
  }catch(SyncTransportFailure invalid){throw invalid;}
  catch(Exception invalid){throw invalid("RESULT_STRUCTURE_INVALID");}
 }
 public SyncResult parse(JsonNode p,String receiptId,String producer,String receiptHash)throws Exception{
  fields(p,"originalEventId,originalEventType,outcome,code,info,processedAt,result");String original=id(p,"originalEventId",64);
  if(!"PRODUCT_SNAPSHOT_CHANGED".equals(text(p,"originalEventType")))throw invalid("UNSUPPORTED_ORIGINAL_TYPE");
  String outcome=text(p,"outcome"),code=id(p,"code",128);text(p,"info");String processed=utc(p,"processedAt");String goods=null,version=null,sale=null;Boolean applied=null;
  if(outcome.equals("REJECTED")){if(code.equals("0000") || !p.get("result").isNull())throw invalid("RESULT_STRUCTURE_INVALID");}
  else if(Set.of("APPLIED","IGNORED").contains(outcome)){
   if(!code.equals("0000"))throw invalid("RESULT_STRUCTURE_INVALID");var result=p.get("result");fields(result,"goodsId,currentVersion,applied,saleStatus");
   goods=id(result,"goodsId",64);version=text(result,"currentVersion");Product.parseVersion(version);sale=text(result,"saleStatus");if(!Set.of("ON_SALE","OFF_SALE").contains(sale) || !result.get("applied").isBoolean())throw invalid("RESULT_STRUCTURE_INVALID");
   applied=result.get("applied").booleanValue();if(applied!=outcome.equals("APPLIED"))throw invalid("RESULT_STRUCTURE_INVALID");
  }else throw invalid("RESULT_STRUCTURE_INVALID");
  var fact=new TreeMap<String,Object>();fact.put("originalEventId",original);fact.put("outcome",outcome);fact.put("code",code);fact.put("processedAt",processed);fact.put("goodsId",goods);fact.put("currentVersion",version);fact.put("applied",applied);fact.put("saleStatus",sale);
  return new SyncResult(receiptId,producer,receiptHash,original,outcome,code,processed,goods,version,applied,sale,ContractCodec.sha256(new ContractCodec().encode(fact)));
 }
 public static void fields(JsonNode n,String list){if(n==null || !n.isObject())throw invalid("RESULT_STRUCTURE_INVALID");var names=new HashSet<String>();n.fieldNames().forEachRemaining(names::add);if(!names.equals(Set.of(list.split(","))))throw invalid("RESULT_STRUCTURE_INVALID");}
 public static String text(JsonNode n,String key){if(n.get(key)==null || !n.get(key).isTextual())throw invalid("RESULT_STRUCTURE_INVALID");return n.get(key).textValue();}
 public static String id(JsonNode n,String key,int max){String value=text(n,key);if(value.isEmpty() || value.length()>max || !value.equals(value.trim()))throw invalid("RESULT_STRUCTURE_INVALID");return value;}
 public static String utc(JsonNode n,String key){String value=text(n,key);if(!value.matches("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{3}Z"))throw invalid("RESULT_STRUCTURE_INVALID");Instant.parse(value);return value;}
 private static SyncTransportFailure invalid(String code){return new SyncTransportFailure(code,true);}
}
