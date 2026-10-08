package cn.zj.zjmarket.verification;
import cn.zj.zjmarket.application.product.*;
import cn.zj.zjmarket.infrastructure.product.*;
import cn.zj.zjmarket.infrastructure.config.MqSettings;
import cn.zj.zjmarket.infrastructure.integration.codec.ContractCodec;
import org.springframework.context.ApplicationContext;
import org.apache.rocketmq.acl.common.*;
import org.apache.rocketmq.client.consumer.*;
import org.apache.rocketmq.client.consumer.listener.*;
import org.apache.rocketmq.client.consumer.rebalance.AllocateMessageQueueAveragely;
import org.apache.rocketmq.client.producer.*;
import org.apache.rocketmq.common.message.Message;
import org.apache.rocketmq.common.consumer.ConsumeFromWhere;
import java.util.*;
import java.util.concurrent.atomic.*;
/** Isolated real Broker retry/dead-letter path; production group remains maxReconsumeTimes=8. */
final class SyncDeadLetter {
 static void verify(ApplicationContext ctx,SyncResultReader reader,SyncTransport.Result fact,List<String> evidence)throws Exception{
  var mq=ctx.getBean(MqSettings.class);var store=ctx.getBean(SyncStore.class);
  var original=SyncCommands.message(mq,fact.originalEventId(),fact.goodsId(),fact.currentVersion(),fact.saleStatus(),fact.outcome(),UUID.randomUUID().toString());
  // Match the existing authoritative fact, including processedAt, so this receipt is never new evidence.
  var tree=(com.fasterxml.jackson.databind.node.ObjectNode)SyncCommands.JSON.readTree(original.body());
  ((com.fasterxml.jackson.databind.node.ObjectNode)tree.path("payload")).put("processedAt",fact.processedAt());
  original=SyncCommands.signed(mq,tree,mq.getAKeyId(),mq.getASecret());
  final var target=original;final String hash=ContractCodec.sha256(target.body());var attempts=new AtomicInteger();var recovered=new AtomicBoolean();
  SyncStore broken=(SyncStore)java.lang.reflect.Proxy.newProxyInstance(SyncStore.class.getClassLoader(),new Class[]{SyncStore.class},(proxy,method,args)->{if(method.getName().equals("accept"))throw new org.springframework.jdbc.CannotGetJdbcConnectionException("controlled verification fault");try{return method.invoke(store,args);}catch(java.lang.reflect.InvocationTargetException e){throw e.getCause();}});
  var failingReader=new SyncResultReader(mq,broken,Map.of(mq.getAKeyId(),mq.getASecret()));
  var retry=consumer(mq,"B_SYNC_RETRY_TEST-dev");var dlq=consumer(mq,"B_SYNC_DLQ_READER-dev");
  var producer=new DefaultMQProducer("B024_A_FIXTURE_"+UUID.randomUUID(),new AclClientRPCHook(new SessionCredentials(SyncCommands.env("B_SYNC_TEST_A_ACCESS_KEY"),SyncCommands.env("B_SYNC_TEST_A_SECRET_KEY"))));producer.setNamesrvAddr(mq.getNameserver());producer.setUseTLS(mq.isUseTls());producer.setRetryTimesWhenSendFailed(0);
  retry.setMaxReconsumeTimes(1);retry.subscribe(mq.getResultTopic(),"EVENT_PROCESSING_RESULT");
  retry.registerMessageListener((MessageListenerConcurrently)(messages,context)->{for(var m:messages){if(!Arrays.equals(m.getBody(),target.body()))continue;attempts.incrementAndGet();try{failingReader.receive(target);throw new IllegalStateException("fault injection missing");}catch(org.springframework.jdbc.CannotGetJdbcConnectionException expected){context.setDelayLevelWhenNextConsume(1);return ConsumeConcurrentlyStatus.RECONSUME_LATER;}}return ConsumeConcurrentlyStatus.CONSUME_SUCCESS;});
  dlq.subscribe("%DLQ%B_SYNC_RETRY_TEST-dev","*");dlq.registerMessageListener((MessageListenerConcurrently)(messages,context)->{for(var m:messages){if(!Arrays.equals(m.getBody(),target.body()))continue;try{SyncCommands.check(Arrays.equals(m.getBody(),target.body()),"DLQ preserves immutable bytes");SyncCommands.check(reader.decode(target).originalEventId().equals(fact.originalEventId()),"trusted recovered DLQ receipt decoded");recovered.set(true);}catch(RuntimeException failure){return ConsumeConcurrentlyStatus.RECONSUME_LATER;}}return ConsumeConcurrentlyStatus.CONSUME_SUCCESS;});
  try{dlq.start();retry.start();producer.start();Thread.sleep(2500);var message=new Message(mq.getResultTopic(),"EVENT_PROCESSING_RESULT",UUID.randomUUID().toString(),target.body());message.putUserProperty("keyId",target.keyId());message.putUserProperty("signature",target.signature());SyncCommands.check(producer.send(message,10000).getSendStatus()==SendStatus.SEND_OK,"A fixture real broker ACK");SyncCommands.waitFor(recovered::get,55000,"isolated DB failure/reconsume/dead-letter/trusted recovery");SyncCommands.check(attempts.get()==2,"one initial consumption plus one isolated retry");evidence.add("actual-RocketMQ/isolated-maxRetry1/DB-fault-port/two-consumptions/DLQ-preserved-bytes/trusted-recovery=PASSED; business-maxRetry8-unchanged");}
  finally{producer.shutdown();retry.shutdown();dlq.shutdown();}
 }
 static DefaultMQPushConsumer consumer(MqSettings mq,String group){var c=new DefaultMQPushConsumer(group,new AclClientRPCHook(new SessionCredentials(mq.getAccessKey(),mq.getSecretKey())),new AllocateMessageQueueAveragely());c.setNamesrvAddr(mq.getNameserver());c.setUseTLS(mq.isUseTls());c.setConsumeFromWhere(ConsumeFromWhere.CONSUME_FROM_FIRST_OFFSET);c.setConsumeThreadMin(1);c.setConsumeThreadMax(1);c.setConsumeMessageBatchMaxSize(1);return c;}
}
