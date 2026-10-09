package cn.zj.zjmarket.infrastructure.adapter.port.product;

import cn.bugstack.api.v2.*;
import cn.zj.zjmarket.domain.product.adapter.port.IProductResultSubscription;
import cn.zj.zjmarket.domain.product.adapter.port.IProductSyncPort;
import cn.zj.zjmarket.domain.product.model.valobj.SyncBadMessage;
import cn.zj.zjmarket.domain.product.model.valobj.SyncQuery;
import cn.zj.zjmarket.domain.product.model.valobj.SyncWork;
import cn.zj.zjmarket.infrastructure.config.properties.MqSettings;
import cn.zj.zjmarket.infrastructure.config.properties.RpcSettings;
import cn.zj.zjmarket.infrastructure.gateway.codec.ContractCodec;
import cn.zj.zjmarket.infrastructure.gateway.mq.MqClientFactory;
import cn.zj.zjmarket.infrastructure.gateway.mq.SyncResultReader;
import cn.zj.zjmarket.infrastructure.gateway.rpc.RpcClientFactory;
import cn.zj.zjmarket.types.exception.SyncTransportFailure;
import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.*;
import org.apache.dubbo.config.ReferenceConfig;
import org.apache.dubbo.rpc.RpcContext;
import org.apache.rocketmq.client.consumer.*;
import org.apache.rocketmq.client.consumer.listener.*;
import org.apache.rocketmq.client.producer.*;
import org.apache.rocketmq.common.consumer.ConsumeFromWhere;
import org.apache.rocketmq.common.message.Message;
/** Lazy SDK lifecycle: startup does not require A or Broker online; errors remain recoverable facts. */
public final class RocketMqSyncTransport implements IProductSyncPort,IProductResultSubscription,AutoCloseable {
 private final RpcSettings rpc;private final MqSettings mq;private final MqClientFactory factory;private final SyncResultReader reader;private final ContractCodec codec=new ContractCodec();
 private final ReferenceConfig<IntegrationService> reference;private final ObjectMapper json=new ObjectMapper();
 private DefaultMQProducer producer;private DefaultMQPushConsumer consumer;
 public RocketMqSyncTransport(RpcSettings rpc,MqSettings mq,RpcClientFactory rpcFactory,MqClientFactory factory,SyncResultReader reader){this.rpc=rpc;this.mq=mq;this.factory=factory;this.reader=reader;reference=rpcFactory.reference(IntegrationService.class);reference.setCheck(false);}
 public synchronized void startConsumer(int retries,boolean accelerated)throws Exception{
  if(consumer!=null)return;var candidate=factory.resultConsumer();candidate.setConsumeFromWhere(ConsumeFromWhere.CONSUME_FROM_FIRST_OFFSET);candidate.setConsumeMessageBatchMaxSize(1);candidate.setMaxReconsumeTimes(retries);
  candidate.subscribe(mq.getResultTopic(),"EVENT_PROCESSING_RESULT");candidate.registerMessageListener((MessageListenerConcurrently)(messages,context) -> {
   try{for(var m:messages)reader.receive(new SyncBadMessage(m.getTopic(),m.getTags(),m.getUserProperty("keyId"),m.getUserProperty("signature"),m.getBody(),null));return ConsumeConcurrentlyStatus.CONSUME_SUCCESS;}
   catch(RuntimeException technical){if(accelerated)context.setDelayLevelWhenNextConsume(1);return ConsumeConcurrentlyStatus.RECONSUME_LATER;}
  });try{candidate.start();consumer=candidate;}catch(Exception e){candidate.shutdown();throw e;}
 }
 private synchronized DefaultMQProducer producer()throws Exception{if(producer==null){var candidate=factory.producer("B_PRODUCT_SYNC_"+UUID.randomUUID());try{candidate.start();producer=candidate;}catch(Exception e){candidate.shutdown();throw e;}}return producer;}
 public void publish(SyncWork w){try{
  byte[] body=validate(w);var message=new Message(mq.getProductTopic(),"PRODUCT_SNAPSHOT_CHANGED",w.eventId(),body);
  message.putUserProperty("source",mq.getSource());message.putUserProperty("channel",mq.getChannel());message.putUserProperty("keyId",mq.getBKeyId());message.putUserProperty("signature",ContractCodec.hmac(mq.getBSecret(),mq.getProductTopic()+"\n"+ContractCodec.sha256(body)));
  if(producer().send(message,mq.getSendTimeoutMillis()).getSendStatus()!=SendStatus.SEND_OK)throw new SyncTransportFailure("SEND_OUTCOME_UNKNOWN",false);
 }catch(SyncTransportFailure e){throw e;}catch(Exception e){throw new SyncTransportFailure("TECH_SEND_FAILED",false);}}
 public SyncQuery query(SyncWork w){try{
  validate(w);var request=new EventResultQueryRequest();request.setEventId(w.eventId());request.setSource(rpc.getSource());request.setChannel(rpc.getChannel());
  byte[] bytes=new byte[24];new SecureRandom().nextBytes(bytes);String timestamp=Long.toString(System.currentTimeMillis()),nonce=Base64.getUrlEncoder().withoutPadding().encodeToString(bytes),requestId=UUID.randomUUID().toString();
  String text=String.join("\n",rpc.getClientId(),rpc.getKeyId(),timestamp,nonce,requestId,IntegrationService.class.getName(),"queryEventResult",rpc.getVersion(),rpc.getGroup(),ContractCodec.sha256(codec.encode(request)));
  var attachments=Map.of("clientId",rpc.getClientId(),"keyId",rpc.getKeyId(),"timestamp",timestamp,"nonce",nonce,"requestId",requestId,"signature",ContractCodec.hmac(rpc.getSecret(),text));
  RpcResult<EventProcessingResult> response;
  try{attachments.forEach((k,v)->RpcContext.getClientAttachment().setAttachment(k,v));response=reference.get().queryEventResult(request);}finally{RpcContext.getClientAttachment().clearAttachments();}
  if(response==null || !requestId.equals(response.getRequestId()))throw new SyncTransportFailure("UPSTREAM_RESPONSE_INVALID",true);
  if("NOT_FOUND".equals(response.getCode()) && response.getData()==null)return new SyncQuery("NOT_FOUND",null);
  if(!"0000".equals(response.getCode())){boolean auth=Set.of("AUTH_REQUIRED","AUTH_INVALID","FORBIDDEN","REPLAY_REJECTED","E0112").contains(response.getCode());throw new SyncTransportFailure(auth?"INTEGRATION_AUTH_FAILED":"TECH_QUERY_FAILED",auth);}
  var data=response.getData();if(data==null || !w.eventId().equals(data.getEventId()) || !"PRODUCT_SNAPSHOT_CHANGED".equals(data.getEventType()))throw new SyncTransportFailure("UPSTREAM_RESPONSE_INVALID",true);
  if("WAITING_DEPENDENCY".equals(data.getProcessingStatus())){if(data.getResult()!=null || data.getOutcome()!=null)throw new SyncTransportFailure("UPSTREAM_RESPONSE_INVALID",true);return new SyncQuery("WAITING_DEPENDENCY",null);}
  if(!"PROCESSED".equals(data.getProcessingStatus()))throw new SyncTransportFailure("UPSTREAM_RESPONSE_INVALID",true);
  ObjectNode payload=json.createObjectNode();payload.put("originalEventId",data.getEventId());payload.put("originalEventType",data.getEventType());payload.put("outcome",data.getOutcome());payload.put("code",data.getCode());payload.put("info",data.getInfo());payload.put("processedAt",data.getProcessedAt());payload.set("result",json.valueToTree(data.getResult()));
  var result=reader.parse(payload,"rpc-"+w.eventId(),mq.getAProducerId(),ContractCodec.sha256(codec.encode(payload)));return new SyncQuery("PROCESSED",result);
 }catch(SyncTransportFailure e){throw e;}catch(Exception e){throw new SyncTransportFailure("TECH_QUERY_FAILED",false);}}
 private byte[] validate(SyncWork w)throws Exception{
  byte[] bytes=w.body().getBytes(StandardCharsets.UTF_8);if(bytes.length>256*1024 || !ContractCodec.sha256(bytes).equals(w.bodyHash()))throw new SyncTransportFailure("LOCAL_FACT_INVALID",true);
  var envelope=json.readTree(bytes);SyncResultReader.fields(envelope,"eventId,eventType,schemaVersion,producer,occurredAt,source,channel,correlationId,payload");
  if(!w.eventId().equals(SyncResultReader.text(envelope,"eventId")) || !mq.getProducerId().equals(SyncResultReader.text(envelope,"producer")) || !mq.getSource().equals(SyncResultReader.text(envelope,"source")) || !mq.getChannel().equals(SyncResultReader.text(envelope,"channel")) || !"PRODUCT_SNAPSHOT_CHANGED".equals(SyncResultReader.text(envelope,"eventType")) || envelope.path("schemaVersion").asInt()!=1)throw new SyncTransportFailure("LOCAL_FACT_INVALID",true);
  var p=envelope.path("payload");SyncResultReader.fields(p,"goodsId,productVersion,goodsName,originalPrice,currency,saleStatus");
  if(!w.goodsId().equals(SyncResultReader.text(p,"goodsId")) || !Long.toString(w.version()).equals(SyncResultReader.text(p,"productVersion")) || !w.saleStatus().equals(SyncResultReader.text(p,"saleStatus")))throw new SyncTransportFailure("LOCAL_FACT_INVALID",true);return bytes;
 }
 public synchronized void stopConsumer(){if(consumer!=null){consumer.shutdown();consumer=null;}}
 public synchronized void close(){stopConsumer();if(producer!=null){producer.shutdown();producer=null;}reference.destroy();}
}
