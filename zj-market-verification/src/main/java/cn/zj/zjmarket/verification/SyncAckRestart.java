package cn.zj.zjmarket.verification;

import cn.zj.zjmarket.domain.product.adapter.repository.IProductSyncRepository;
import cn.zj.zjmarket.domain.product.model.valobj.SaleStatus;
import cn.zj.zjmarket.domain.product.model.valobj.SyncBadMessage;
import cn.zj.zjmarket.domain.product.service.IProductService;
import cn.zj.zjmarket.domain.product.service.IProductSyncService;
import cn.zj.zjmarket.infrastructure.config.properties.MqSettings;
import cn.zj.zjmarket.infrastructure.gateway.codec.ContractCodec;
import cn.zj.zjmarket.infrastructure.gateway.mq.MqClientFactory;
import cn.zj.zjmarket.infrastructure.gateway.mq.SyncResultReader;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.atomic.*;
import javax.sql.DataSource;
import org.apache.rocketmq.client.consumer.listener.*;
import org.apache.rocketmq.common.consumer.ConsumeFromWhere;
import org.springframework.context.ApplicationContext;
/** Test-only process halt after durable real A result, before Broker ACK. Normal app excludes verification. */
final class SyncAckRestart {
 static void run(ApplicationContext ctx,Path work,String mode)throws Exception {
  SyncCommands.guard();var products=ctx.getBean(IProductService.class);var reader=ctx.getBean(SyncResultReader.class);var db=ctx.getBean(DataSource.class);var manifest=work.resolve("ack-fixture.json");var marker=work.resolve("ack-committed.json");boolean commit=mode.equals("ack-commit");
  if(commit){SyncCommands.check(!Files.exists(manifest),"new ack fixture only");var p=products.create(SyncCommands.fields("消费提交后未ACK重启",SaleStatus.ON_SALE),"b026-ack-window");Files.write(manifest,new ContractCodec().encode(SyncCommands.saved(p,ctx.getBean(IProductSyncRepository.class))));}
  var fixture=SyncCommands.JSON.readTree(Files.readAllBytes(manifest));String event=fixture.path("eventId").asText(),goods=fixture.path("goodsId").asText();
  var expected=commit?null:SyncCommands.JSON.readTree(Files.readAllBytes(marker));var completed=new AtomicBoolean();var problem=new AtomicReference<Throwable>();
  var mq=ctx.getBean(MqSettings.class);var consumer=ctx.getBean(MqClientFactory.class).resultConsumer();consumer.setConsumeFromWhere(ConsumeFromWhere.CONSUME_FROM_FIRST_OFFSET);consumer.setConsumeMessageBatchMaxSize(1);consumer.setMaxReconsumeTimes(8);consumer.subscribe(mq.getResultTopic(),"EVENT_PROCESSING_RESULT");
  consumer.registerMessageListener((MessageListenerConcurrently)(messages,context)->{
   try{for(var message:messages){
    boolean accepted=reader.receive(new SyncBadMessage(message.getTopic(),message.getTags(),message.getUserProperty("keyId"),message.getUserProperty("signature"),message.getBody(),null));
    if(!accepted)continue;
    var envelope=SyncCommands.JSON.readTree(message.getBody());if(!event.equals(envelope.path("payload").path("originalEventId").asText()))continue;
    SyncCommands.check(products.detail(goods,true).sync().ready(1),"durable confirmed result before acknowledgement");SyncCommands.check(SyncCommands.count(db,"SELECT COUNT(*) FROM b_sync_inbox WHERE consumer='PRODUCT_SYNC_MQ' AND original_event_id=?",event)==1,"exactly one durable Inbox receipt");
    String receipt=envelope.path("eventId").asText(),hash=ContractCodec.sha256(message.getBody());
    if(commit){Files.write(marker,new ContractCodec().encode(Map.of("eventId",event,"goodsId",goods,"receiptId",receipt,"bodyHash",hash,"processId",ProcessHandle.current().pid())));Runtime.getRuntime().halt(86);}
    SyncCommands.check(expected.path("receiptId").asText().equals(receipt) && expected.path("bodyHash").asText().equals(hash),"Broker redelivers identical committed receipt after hard process restart");SyncCommands.check(expected.path("processId").asLong()!=ProcessHandle.current().pid(),"new consumer process");completed.set(true);
   }return ConsumeConcurrentlyStatus.CONSUME_SUCCESS;}catch(Exception failure){problem.compareAndSet(null,failure);return ConsumeConcurrentlyStatus.RECONSUME_LATER;}
  });
  try{consumer.start();if(commit)SyncCommands.check(ctx.getBean(IProductSyncService.class).publishOne(event),"publish owned real-A ack fixture");SyncCommands.waitFor(()->{if(problem.get()!=null)throw new IllegalStateException("check: ACK recovery consumer failure",problem.get());return completed.get();},60000,"real Broker committed-result redelivery after hard restart");}
  finally{consumer.shutdown();}
  Files.write(work.resolve("ack-recovery.txt"),List.of("status=PASSED","actual-A-signed-result/MySQL-commit/hard-halt-before-Broker-ACK/new-process-identical-receipt/Inbox-count1/current-confirmation-unchanged/business-maxRetry8=PASSED"));
 }
}
