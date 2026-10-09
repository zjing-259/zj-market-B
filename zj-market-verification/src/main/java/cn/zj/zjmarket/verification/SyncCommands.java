package cn.zj.zjmarket.verification;

import cn.zj.zjmarket.ZjMarketApplication;
import cn.zj.zjmarket.domain.identity.service.IIdentityService;
import cn.zj.zjmarket.domain.product.adapter.port.IProductSyncPort;
import cn.zj.zjmarket.domain.product.adapter.repository.IProductSyncRepository;
import cn.zj.zjmarket.domain.product.model.valobj.ProductFields;
import cn.zj.zjmarket.domain.product.model.valobj.ProductView;
import cn.zj.zjmarket.domain.product.model.valobj.SaleStatus;
import cn.zj.zjmarket.domain.product.model.valobj.SyncBadMessage;
import cn.zj.zjmarket.domain.product.model.valobj.SyncQuery;
import cn.zj.zjmarket.domain.product.model.valobj.SyncResult;
import cn.zj.zjmarket.domain.product.model.valobj.SyncWork;
import cn.zj.zjmarket.domain.product.service.IProductService;
import cn.zj.zjmarket.domain.product.service.IProductSyncService;
import cn.zj.zjmarket.domain.product.service.impl.ProductSyncService;
import cn.zj.zjmarket.infrastructure.adapter.port.product.RocketMqSyncTransport;
import cn.zj.zjmarket.infrastructure.adapter.repository.ProductSyncRepository;
import cn.zj.zjmarket.infrastructure.config.properties.MqSettings;
import cn.zj.zjmarket.infrastructure.dao.IProductDao;
import cn.zj.zjmarket.infrastructure.dao.IProductSyncDao;
import cn.zj.zjmarket.infrastructure.gateway.codec.ContractCodec;
import cn.zj.zjmarket.infrastructure.gateway.mq.MqClientFactory;
import cn.zj.zjmarket.infrastructure.gateway.mq.SyncResultReader;
import cn.zj.zjmarket.types.exception.ProductFailure;
import cn.zj.zjmarket.types.exception.SyncTransportFailure;
import com.fasterxml.jackson.databind.*;
import java.nio.file.*;
import java.time.*;
import java.util.*;
import javax.sql.DataSource;
import org.springframework.boot.*;
import org.springframework.boot.web.server.context.WebServerApplicationContext;
/** Explicit real integration / fault-matrix verification. Normal application excludes this class. */
public final class SyncCommands {
 static final ObjectMapper JSON=new ObjectMapper();static final List<String> evidence=new ArrayList<>();
 public static int run(String mode,String id){try{
  if(!Set.of("prepare","prepare-browser","verify","replay","ack-commit","ack-recover").contains(mode))throw new IllegalArgumentException("Unsupported sync command");
  if(!mode.equals("replay"))guard();
  var app=new SpringApplication(ZjMarketApplication.class);if(!mode.equals("verify"))app.setWebApplicationType(WebApplicationType.NONE);
  try(var ctx=app.run("--server.port=0","--b.identity.enabled=true","--b.product.enabled=true","--b.trial.enabled=false","--b.sync.enabled=true","--b.sync.scheduler-enabled=false","--b.infrastructure.database.enabled=true","--b.infrastructure.rpc.enabled=true","--b.infrastructure.mq.enabled=true")){
   var products=ctx.getBean(IProductService.class);var store=ctx.getBean(IProductSyncRepository.class);var service=ctx.getBean(IProductSyncService.class);var transport=ctx.getBean(RocketMqSyncTransport.class);var reader=ctx.getBean(SyncResultReader.class);var db=ctx.getBean(DataSource.class);
   if(mode.equals("replay")){if(id==null)throw new IllegalArgumentException("Quarantine id required");reader.replay(id);System.out.println("B quarantine trusted replay: PASSED");return 0;}
   var work=Path.of(env("B_SYNC_WORK"));Files.createDirectories(work);var fixtureFile=work.resolve("fixtures.json");
   if(mode.startsWith("ack-")){SyncAckRestart.run(ctx,work,mode);return 0;}
   if(mode.equals("prepare-browser")){
    var p=products.create(fields("运营同步页面验收",SaleStatus.ON_SALE),"b024-browser");service.pause(p.product().goodsId(),p.sync().targetEventId(),1,"verification-operator");Files.write(work.resolve("browser-fixture.json"),new ContractCodec().encode(saved(p,store)));System.out.println("B owned paused browser fixture: PASSED");return 0;
   }
   if(mode.equals("prepare")){
    check(!Files.exists(fixtureFile),"refuse to overwrite fixture manifest");
    var persisted=products.create(fields("提交后待恢复",SaleStatus.ON_SALE),"b024-before-restart");
    var uncertain=products.create(fields("发送后未记录Broker确认",SaleStatus.OFF_SALE),"b024-crash-window");
    var queued=products.create(fields("发送结果丢失后受控重投",SaleStatus.ON_SALE),"b024-uncertain-result");
    var fixtures=new LinkedHashMap<String,Object>();fixtures.put("persisted",saved(persisted,store));fixtures.put("uncertain",saved(uncertain,store));fixtures.put("queued",saved(queued,store));
    check(service.publishOne(persisted.sync().targetEventId()),"publish while A offline");check(store.event(persisted.sync().targetEventId()).deliveryState().equals("PUBLISHED"),"SEND_OK recorded independently");
    check(!products.detail(persisted.product().goodsId(),true).sync().ready(1),"broker confirmation not A confirmation");
    forceDue(db,persisted.sync().targetEventId());check(service.queryOne(persisted.sync().targetEventId()) && store.event(persisted.sync().targetEventId()).queryAttempts()==1,"offline query remains recoverable");
    var claim=store.claim("SEND",uncertain.sync().targetEventId(),30000);check(claim!=null,"crash-window lease");transport.publish(claim); // Deliberately leave lease/ack unresolved before process exit.
    Files.write(fixtureFile,new ContractCodec().encode(fixtures));Files.write(work.resolve("prepare.txt"),List.of("status=PASSED","A offline: commit/publish/PENDING; immutable original body retained; business commit and send-before-ack crash fixtures persisted"));
    System.out.println("B sync phase prepare/A-offline: PASSED");return 0;
   }
   evidence.add("java="+Runtime.version());evidence.add("springBoot="+SpringBootVersion.getVersion());
   SyncLeaseRegression.verify(products,store,db,evidence);
   localMatrix(products,store,service,reader,db,ctx.getBean(MqSettings.class));
   var fixtures=JSON.readTree(Files.readAllBytes(fixtureFile));var original=fixtures.path("persisted");String event=original.path("eventId").asText(),goods=original.path("goodsId").asText();
   forceDue(db,event);waitFor(() -> {service.queryOne(event);return products.detail(goods,true).sync().ready(1);},50000,"RPC restores missed result after process restart");
   check(store.event(event).bodyHash().equals(original.path("bodyHash").asText()),"persisted immutable body after restart");
   evidence.add("actual-A-offline/commit/SEND_OK-not-confirmed/B-restart/RPC-durable-result-recovery=PASSED");
   var uncertain=fixtures.path("uncertain");String crashId=uncertain.path("eventId").asText();sql(db,"UPDATE b_product_outbox SET lease_until_ms=0,next_send_ms=0 WHERE event_id=?",crashId);
   check(service.publishOne(crashId),"reclaim crashed publisher and re-publish same event");forceDue(db,crashId);
   waitFor(() -> {service.queryOne(crashId);return products.detail(uncertain.path("goodsId").asText(),true).sync().ready(1);},50000,"uncertain send idempotent recovery");
   check(store.event(crashId).bodyHash().equals(uncertain.path("bodyHash").asText()),"no new body on retry");evidence.add("actual-Broker-send-before-ack/process-restart/original-event-redelivery=PASSED");
   transport.startConsumer(8,false);
   var mqProduct=products.create(fields("真实MQ消费确认",SaleStatus.ON_SALE),"b024-real-result");String mqEvent=mqProduct.sync().targetEventId();check(service.publishOne(mqEvent),"normal publish");
   waitFor(() -> products.detail(mqProduct.product().goodsId(),true).sync().ready(1),55000,"production MQ signed result confirms");
   check(count(db,"SELECT COUNT(*) FROM b_sync_inbox WHERE consumer='PRODUCT_SYNC_MQ' AND original_event_id=?",mqEvent)>=1,"production Inbox durable");
   evidence.add("actual-RocketMQ/8-retry-business-group/signed-result/production-Inbox+progress=PASSED");
   actualVersionMatrix(ctx,products,store,service,transport);
   var queued=fixtures.path("queued");String queuedId=queued.path("eventId").asText();
   // Real Broker ACK with an unmatched Tag: A does not consume/apply the fact.
   try(varFixtureProducer p=new varFixtureProducer(ctx.getBean(MqClientFactory.class),ctx.getBean(MqSettings.class))){p.sendWrongTag(store.event(queuedId));}
   var claim=store.claim("SEND",queuedId,30000);check(claim!=null,"missing-result lease");store.sent(claim,2000);forceDue(db,queuedId);
   check(service.queryOne(queuedId) && service.progress(queued.path("goodsId").asText()).state().equals("PENDING"),"actual NOT_FOUND remains pending");
   String beforeHash=store.event(queuedId).bodyHash();service.retry(queued.path("goodsId").asText(),queuedId,1,"verification-operator");check(service.publishOne(queuedId),"controlled same event retry");
   waitFor(() -> products.detail(queued.path("goodsId").asText(),true).sync().ready(1),55000,"controlled redelivery converges");check(store.event(queuedId).bodyHash().equals(beforeHash),"controlled retry preserves bytes");
   evidence.add("actual-Broker-ACK-but-NOT_FOUND/controlled-query-before-retry/original-event-convergence=PASSED");
   httpMatrix(ctx,products,store,service);
   // Stop only this verification process's business consumer, leaving shared Broker/A untouched.
   transport.stopConsumer();var dlqProduct=products.create(fields("死信后RPC补查确认",SaleStatus.ON_SALE),"dlq-rpc-recovery");String dlqId=dlqProduct.sync().targetEventId();service.publishOne(dlqId);
   var dlqFact=new java.util.concurrent.atomic.AtomicReference<SyncResult>();waitFor(() -> {var q=transport.query(store.event(dlqId));if(q.status().equals("PROCESSED")){dlqFact.set(q.result());return true;}return false;},45000,"actual A persisted result while owned consumer unavailable");
   check(service.progress(dlqProduct.product().goodsId()).state().equals("PENDING"),"pending retained before DLQ recovery");SyncDeadLetter.verify(ctx,reader,dlqFact.get(),evidence);
   forceDue(db,dlqId);check(service.queryOne(dlqId) && products.detail(dlqProduct.product().goodsId(),true).sync().ready(1),"actual RPC confirms pending fact after isolated dead-letter");evidence.add("actual-pending-before-DLQ/RPC-authoritative-recovery-after-DLQ=PASSED");
   var browserFixture=products.create(fields("运营同步页面验收",SaleStatus.ON_SALE),"b024-browser");service.pause(browserFixture.product().goodsId(),browserFixture.sync().targetEventId(),1,"verification-operator");Files.write(work.resolve("browser-fixture.json"),new ContractCodec().encode(saved(browserFixture,store)));
   evidence.add("status=PASSED");Files.write(work.resolve("verify.txt"),evidence);System.out.println("B reliable synchronization real integration: PASSED");
  }return 0;
 }catch(Exception e){System.err.println("B sync command failed: "+e.getClass().getSimpleName()+" "+(e.getMessage()!=null && e.getMessage().startsWith("check:")?e.getMessage():"details withheld"));return 1;}}
 static Map<String,String> saved(ProductView p,IProductSyncRepository store){return Map.of("goodsId",p.product().goodsId(),"eventId",p.sync().targetEventId(),"bodyHash",store.event(p.sync().targetEventId()).bodyHash());}
 static ProductFields fields(String name,SaleStatus status){return new ProductFields(name,"可靠同步验收",null,"88.50","CNY",status);}
 interface Checked {boolean get()throws Exception;}
 static void waitFor(Checked condition,long ms,String name)throws Exception{long end=System.nanoTime()+ms*1000000;while(!condition.get()){if(System.nanoTime()>end)throw new IllegalStateException("check: "+name);Thread.sleep(200);}System.out.println("B sync check: "+name+" PASSED");}
 static void guard(){if(!"b02-test".equals(env("B_DATABASE_SCOPE")) || !env("B_DATABASE_URL").matches("^jdbc:mysql://[^/]+/zj_market_b02_test(?:\\?.*)?$") || !"zj_market_b02_test_app".equals(env("B_DATABASE_USERNAME")))throw new IllegalArgumentException("Exact isolated B test database required");}
 static String env(String key){var value=System.getenv(key);if(value==null || value.isBlank())throw new IllegalArgumentException("Missing external configuration");return value;}
 static void check(boolean v,String name){if(!v)throw new IllegalStateException("check: "+name);}
 static void sql(DataSource db,String sql,String id)throws Exception{try(var c=db.getConnection();var p=c.prepareStatement(sql)){p.setString(1,id);p.executeUpdate();}}
 static long count(DataSource db,String sql,String id)throws Exception{try(var c=db.getConnection();var p=c.prepareStatement(sql)){p.setString(1,id);try(var rows=p.executeQuery()){rows.next();return rows.getLong(1);}}}
 static void forceDue(DataSource db,String id)throws Exception{sql(db,"UPDATE b_product_outbox SET next_query_ms=0 WHERE event_id=?",id);}

 static void localMatrix(IProductService products,IProductSyncRepository store,IProductSyncService real,SyncResultReader reader,DataSource db,MqSettings mq)throws Exception{
  var p=products.create(fields("去重乱序故障矩阵",SaleStatus.ON_SALE),"b024-fixture");String goods=p.product().goodsId(),first=p.sync().targetEventId();
  var firstResult=message(mq,first,goods,"1","ON_SALE","APPLIED",UUID.randomUUID().toString());check(reader.receive(firstResult),"verified first result");check(reader.receive(firstResult),"duplicate receipt ACK");
  check(count(db,"SELECT COUNT(*) FROM b_sync_inbox WHERE original_event_id=?",first)==1,"Inbox duplicate no new row");
  var v2=products.edit(goods,1,fields("版本2",SaleStatus.ON_SALE),"edit2");var v3=products.edit(goods,2,fields("版本3",SaleStatus.OFF_SALE),"edit3");
  check(reader.receive(message(mq,v2.sync().targetEventId(),goods,"2","ON_SALE","APPLIED",UUID.randomUUID().toString())),"older receipt applied history");
  check(products.detail(goods,true).sync().targetVersion().equals("3") && products.detail(goods,true).sync().state().equals("PENDING"),"older receipt cannot confirm newer target");
  var latest=message(mq,v3.sync().targetEventId(),goods,"3","OFF_SALE","APPLIED",UUID.randomUUID().toString());check(reader.receive(latest),"latest receipt");check(products.detail(goods,true).sync().ready(3),"latest confirmed");
  var changed=JSON.readTree(firstResult.body());((com.fasterxml.jackson.databind.node.ObjectNode)changed.path("payload")).put("info","changed-body");check(!reader.receive(signed(mq,changed,mq.getAKeyId(),mq.getASecret())),"same receipt different bytes quarantined");
  check(products.detail(goods,true).sync().ready(3),"old receipt conflict cannot alter new target");
  var contradiction=message(mq,v3.sync().targetEventId(),goods,"2","OFF_SALE","IGNORED",UUID.randomUUID().toString());check(!reader.receive(contradiction),"contradictory result preserved and quarantined");check(products.detail(goods,true).sync().state().equals("RECONCILIATION_REQUIRED") && products.detail(goods,true).product().version()==3,"contradiction cannot rewrite product");
  var repeat=(com.fasterxml.jackson.databind.node.ObjectNode)JSON.readTree(latest.body());repeat.put("eventId",UUID.randomUUID().toString());check(reader.receive(signed(mq,repeat,mq.getAKeyId(),mq.getASecret())),"repeated first fact still ACKs after conflict");check(products.detail(goods,true).sync().state().equals("RECONCILIATION_REQUIRED"),"conflicting evidence never disappears on later original receipt");
  var ignored=products.create(fields("同版本IGNORED",SaleStatus.OFF_SALE),"same-version");check(reader.receive(message(mq,ignored.sync().targetEventId(),ignored.product().goodsId(),"1","OFF_SALE","IGNORED",UUID.randomUUID().toString())) && products.detail(ignored.product().goodsId(),true).sync().ready(1),"same-version IGNORED confirms");
  var terminal=products.create(fields("已确认时A离线也不能重投",SaleStatus.OFF_SALE),"terminal-retry");String terminalId=terminal.sync().targetEventId();store.sent(store.claim("SEND",terminalId,30000),2000);check(reader.receive(message(mq,terminalId,terminal.product().goodsId(),"1","OFF_SALE","APPLIED",UUID.randomUUID().toString())),"terminal fixture confirmed");
  var noNetwork=new IProductSyncPort(){public void publish(SyncWork w){throw new AssertionError("terminal publish forbidden");}public SyncQuery query(SyncWork w){throw new AssertionError("terminal query forbidden");}};
  try{new ProductSyncService(store,noNetwork,30000,2000,2000,8000).retry(terminal.product().goodsId(),terminalId,1,"verification-operator");throw new IllegalStateException("check: terminal retry must reject locally");}catch(ProductFailure expected){check(expected.status()==409,"terminal retry locally rejects even A unavailable");}
  var newer=products.create(fields("A较大版本不能确认",SaleStatus.OFF_SALE),"greater-version");check(reader.receive(message(mq,newer.sync().targetEventId(),newer.product().goodsId(),"2","OFF_SALE","IGNORED",UUID.randomUUID().toString())) && products.detail(newer.product().goodsId(),true).sync().state().equals("RECONCILIATION_REQUIRED"),"larger version needs reconciliation");
  var rejected=products.create(fields("确定业务拒绝",SaleStatus.OFF_SALE),"reject");check(reader.receive(message(mq,rejected.sync().targetEventId(),rejected.product().goodsId(),null,null,"REJECTED",UUID.randomUUID().toString())),"business rejection ACK after persistence");
  check(store.claim("SEND",rejected.sync().targetEventId(),30000)==null,"rejection never automatic retry");
  try{real.retry(rejected.product().goodsId(),rejected.sync().targetEventId(),1,"verification-operator");throw new IllegalStateException("check: rejection retry expected");}catch(ProductFailure expected){check(expected.status()==409,"rejected retry denied");}
  var bad=message(mq,first,goods,"1","ON_SALE","APPLIED",UUID.randomUUID().toString());long qBefore=store.quarantined(1,100).total();
  var badSignature=new SyncBadMessage(bad.topic(),bad.tag(),bad.keyId(),"invalid",bad.body(),null);check(!reader.receive(badSignature) && !reader.receive(badSignature),"invalid signature quarantined");check(store.quarantined(1,100).total()==qBefore+1,"quarantine deduplicates");
  for(String change:List.of("schema","schema-overflow","schema-bigint","trailing-object","producer","channel","unknown","boolean","duplicate")){
   var tree=(com.fasterxml.jackson.databind.node.ObjectNode)JSON.readTree(bad.body());
   switch(change){case "schema"->tree.put("schemaVersion",2);case "schema-overflow"->tree.put("schemaVersion",4294967297L);case "schema-bigint"->tree.put("schemaVersion",new java.math.BigInteger("18446744073709551617"));case "producer"->tree.put("producer","rogue");case "channel"->tree.put("channel","other");case "unknown"->((com.fasterxml.jackson.databind.node.ObjectNode)tree.path("payload")).put("unknown",true);case "boolean"->((com.fasterxml.jackson.databind.node.ObjectNode)tree.path("payload").path("result")).put("applied",false);default->{}}
   var invalid=signed(mq,tree,mq.getAKeyId(),mq.getASecret());if(change.equals("duplicate")){String raw=new String(invalid.body(),java.nio.charset.StandardCharsets.UTF_8).replace("\"schemaVersion\":1","\"schemaVersion\":1,\"schemaVersion\":1");byte[] bytes=raw.getBytes(java.nio.charset.StandardCharsets.UTF_8);invalid=new SyncBadMessage(mq.getResultTopic(),"EVENT_PROCESSING_RESULT",mq.getAKeyId(),ContractCodec.hmac(mq.getASecret(),mq.getResultTopic()+"\n"+ContractCodec.sha256(bytes)),bytes,null);}
   if(change.equals("trailing-object")){byte[] bytes=(new String(invalid.body(),java.nio.charset.StandardCharsets.UTF_8)+"{}").getBytes(java.nio.charset.StandardCharsets.UTF_8);invalid=new SyncBadMessage(mq.getResultTopic(),"EVENT_PROCESSING_RESULT",mq.getAKeyId(),ContractCodec.hmac(mq.getASecret(),mq.getResultTopic()+"\n"+ContractCodec.sha256(bytes)),bytes,null);}
   long beforePoison=store.quarantined(1,100).total();
   check(!reader.receive(invalid),"strict poison "+change);
   check(store.quarantined(1,100).total()==beforePoison+1,"strict poison durably isolated "+change);
  }
  IProductSyncRepository broken=(IProductSyncRepository)java.lang.reflect.Proxy.newProxyInstance(IProductSyncRepository.class.getClassLoader(),new Class[]{IProductSyncRepository.class},(proxy,method,args)->{if(method.getName().equals("quarantine"))throw new org.springframework.jdbc.CannotGetJdbcConnectionException("controlled failure");try{return method.invoke(store,args);}catch(java.lang.reflect.InvocationTargetException e){throw e.getCause();}});
  try{new SyncResultReader(mq,broken,Map.of(mq.getAKeyId(),mq.getASecret())).receive(badSignature);throw new IllegalStateException("check: quarantine failure must retry");}catch(org.springframework.jdbc.CannotGetJdbcConnectionException expected){}
  var rotation=products.create(fields("旧密钥受控恢复",SaleStatus.OFF_SALE),"rotation");var rotationMessage=message(mq,rotation.sync().targetEventId(),rotation.product().goodsId(),"1","OFF_SALE","APPLIED",UUID.randomUUID().toString());var old=signed(mq,JSON.readTree(rotationMessage.body()),"old-learning-key","public-fixture-secret");check(!reader.receive(old),"unknown key quarantine");String quarantineId=store.quarantine(new SyncBadMessage(old.topic(),old.tag(),old.keyId(),old.signature(),old.body(),"SIGNATURE_INVALID"));
  new SyncResultReader(mq,store,Map.of(mq.getAKeyId(),mq.getASecret(),"old-learning-key","public-fixture-secret")).replay(quarantineId);check(products.detail(rotation.product().goodsId(),true).sync().ready(1),"trusted old-key replay after configuration repair");
  var lease=products.create(fields("租约fencing",SaleStatus.OFF_SALE),"lease");String leaseId=lease.sync().targetEventId();var stale=store.claim("SEND",leaseId,30000);check(stale!=null && store.claim("SEND",leaseId,30000)==null,"concurrent lease excludes other worker");sql(db,"UPDATE b_product_outbox SET lease_until_ms=0 WHERE event_id=?",leaseId);var fresh=store.claim("SEND",leaseId,30000);check(fresh!=null && !fresh.leaseToken().equals(stale.leaseToken()),"expired lease new token");store.sent(stale,2000);check(store.event(leaseId).deliveryState().equals("PENDING"),"expired holder cannot acknowledge");store.sent(fresh,2000);check(store.event(leaseId).deliveryState().equals("PUBLISHED"),"new holder fenced ACK");
  var faults=products.create(fields("技术失败保留原事实",SaleStatus.OFF_SALE),"fail");String failId=faults.sync().targetEventId();var failing=new IProductSyncPort(){public void publish(SyncWork w){throw new SyncTransportFailure("TECH_SEND_FAILED",false);}public SyncQuery query(SyncWork w){return new SyncQuery("NOT_FOUND",null);}};
  var failureService=new ProductSyncService(store,failing,30000,2000,2000,8000);String hash=store.event(failId).bodyHash();for(int i=0;i<6;i++){sql(db,"UPDATE b_product_outbox SET next_send_ms=0 WHERE event_id=?",failId);check(failureService.publishOne(failId),"continued technical retry "+i);}check(store.event(failId).sendFailures()==6 && serviceState(store,faults).equals("PENDING"),"5 failures alert does not discard or stop recovery");
  failureService.pause(faults.product().goodsId(),failId,1,"verification-operator");check(store.claim("SEND",failId,30000)==null,"operator pause durable");failureService.retry(faults.product().goodsId(),failId,1,"verification-operator");check(store.event(failId).bodyHash().equals(hash),"resume retains original event");
  var waiting=new IProductSyncPort(){public void publish(SyncWork w){}public SyncQuery query(SyncWork w){return new SyncQuery("WAITING_DEPENDENCY",null);}};sql(db,"UPDATE b_product_outbox SET delivery_state='PUBLISHED',next_query_ms=0 WHERE event_id=?",failId);check(new ProductSyncService(store,waiting,30000,2000,2000,8000).queryOne(failId) && serviceState(store,faults).equals("PENDING"),"WAITING dependency not applied");
  rollback(products,store,reader,db,mq);
  evidence.add("real-B-MySQL/signed-fixtures: duplicate/old/new/IGNORED/conflict/rejection/strict-poison/quarantine-failure/key-repair=PASSED");evidence.add("real-DB-leases/fencing/5-failure-alert/continued-retry/pause/resume/WAITING=PASSED (controlled fixture time/fault inputs)");
 }
 static String serviceState(IProductSyncRepository store,ProductView v){return store.progress(v.product().goodsId()).state();}
 static void rollback(IProductService products,IProductSyncRepository real,SyncResultReader reader,DataSource db,MqSettings mq)throws Exception{
  var p=products.create(fields("Inbox进度整体回滚",SaleStatus.OFF_SALE),"rollback");String id=p.sync().targetEventId();var body=message(mq,id,p.product().goodsId(),"1","OFF_SALE","APPLIED",UUID.randomUUID().toString());
  var f=new org.mybatis.spring.SqlSessionFactoryBean();f.setDataSource(db);var c=new org.apache.ibatis.session.Configuration();c.addMapper(IProductSyncDao.class);c.addMapper(IProductDao.class);c.setLocalCacheScope(org.apache.ibatis.session.LocalCacheScope.STATEMENT);f.setConfiguration(c);var session=new org.mybatis.spring.SqlSessionTemplate(f.getObject());var actual=session.getMapper(IProductSyncDao.class);
  IProductSyncDao failing=(IProductSyncDao)java.lang.reflect.Proxy.newProxyInstance(IProductSyncDao.class.getClassLoader(),new Class[]{IProductSyncDao.class},(proxy,method,args)->{try{var value=method.invoke(actual,args);if(method.getName().equals("result"))throw new IllegalStateException("controlled transaction fault");return value;}catch(java.lang.reflect.InvocationTargetException e){throw e.getCause();}});
  var tx=new org.springframework.transaction.support.TransactionTemplate(new org.springframework.jdbc.datasource.DataSourceTransactionManager(db));var store=new ProductSyncRepository(failing,session.getMapper(IProductDao.class),tx);
  try{store.accept(reader.decode(body),"PRODUCT_SYNC_MQ");throw new IllegalStateException("check: result failure expected");}catch(IllegalStateException expected){check(expected.getMessage().equals("controlled transaction fault"),"transaction fault recognized");}
  check(real.event(id).processingState().equals("WAITING") && real.progress(p.product().goodsId()).state().equals("PENDING") && count(db,"SELECT COUNT(*) FROM b_sync_inbox WHERE original_event_id=?",id)==0,"Inbox/outbox/progress all rolled back");check(reader.receive(body),"redelivery succeeds after failed commit");evidence.add("actual-MyBatis-result-write-failure/Inbox+outcome+progress-rollback/redelivery=PASSED");
 }
 static SyncBadMessage message(MqSettings mq,String original,String goods,String version,String sale,String outcome,String receipt)throws Exception{
  String time=java.time.format.DateTimeFormatter.ofPattern("uuuu-MM-dd'T'HH:mm:ss.SSS'Z'").withZone(java.time.ZoneOffset.UTC).format(java.time.Instant.now());var result=new LinkedHashMap<String,Object>();if(!outcome.equals("REJECTED")){result.put("goodsId",goods);result.put("currentVersion",version);result.put("applied",outcome.equals("APPLIED"));result.put("saleStatus",sale);}
  var payload=new LinkedHashMap<String,Object>();payload.put("originalEventId",original);payload.put("originalEventType","PRODUCT_SNAPSHOT_CHANGED");payload.put("outcome",outcome);payload.put("code",outcome.equals("REJECTED")?"PRODUCT_VERSION_CONFLICT":"0000");payload.put("info","verification fixture");payload.put("processedAt",time);payload.put("result",outcome.equals("REJECTED")?null:result);
  var envelope=new LinkedHashMap<String,Object>();envelope.put("eventId",receipt);envelope.put("eventType","EVENT_PROCESSING_RESULT");envelope.put("schemaVersion",1);envelope.put("producer",mq.getAProducerId());envelope.put("occurredAt",time);envelope.put("source",mq.getSource());envelope.put("channel",mq.getChannel());envelope.put("correlationId",original);envelope.put("payload",payload);return signed(mq,JSON.valueToTree(envelope),mq.getAKeyId(),mq.getASecret());
 }
 static SyncBadMessage signed(MqSettings mq,JsonNode body,String key,String secret)throws Exception{byte[] bytes=new ContractCodec().encode(body);return new SyncBadMessage(mq.getResultTopic(),"EVENT_PROCESSING_RESULT",key,ContractCodec.hmac(secret,mq.getResultTopic()+"\n"+ContractCodec.sha256(bytes)),bytes,null);}
 static void httpMatrix(org.springframework.context.ConfigurableApplicationContext ctx,IProductService products,IProductSyncRepository store,IProductSyncService service)throws Exception{
  var identity=ctx.getBean(IIdentityService.class);String suffix=UUID.randomUUID().toString().replace("-","").substring(0,12),pass="Sync-"+UUID.randomUUID();identity.register("s"+suffix,pass,"sync user");identity.initializeOperator("o"+suffix,pass,"sync operator");
  var client=new ProductCommands.Client("http://127.0.0.1:"+((WebServerApplicationContext)ctx).getWebServer().getPort(),env("B_IDENTITY_ORIGIN"));String user=client.login("s"+suffix,pass),op=client.login("o"+suffix,pass);
  var p=products.create(fields("HTTP受控恢复",SaleStatus.OFF_SALE),"http");String path="/admin/products/"+p.product().goodsId()+"/sync";var body=Map.of("eventId",p.sync().targetEventId(),"expectedVersion","1");
  client.call("GET",path,null,null,401);client.call("GET",path,null,user,403);client.call("GET",path,null,op,200);client.call("GET",path+"?userId=spoof",null,op,400);
  client.call("POST",path+"/retries",body,user,403);client.call("POST",path+"/pauses",body,op,200);check(store.event(p.sync().targetEventId()).paused(),"HTTP pause persisted");client.call("POST",path+"/retries",body,op,202);client.call("POST",path+"/retries",body,op,202);check(!store.event(p.sync().targetEventId()).paused(),"HTTP resumes original event");
  client.call("POST",path+"/retries",Map.of("eventId",p.sync().targetEventId(),"expectedVersion","2"),op,409);client.call("POST",path+"/retries",Map.of("eventId",p.sync().targetEventId(),"expectedVersion",1),op,400);
  client.call("GET","/admin/sync/quarantine",null,null,401);client.call("GET","/admin/sync/quarantine",null,user,403);client.call("GET","/%61dmin/sync/quarantine",null,user,403);var page=client.call("GET","/admin/sync/quarantine?size=100",null,op,200);
  for(var item:page.path("data").path("items"))check(item.size()==6 && !item.has("body") && !item.has("signature") && !item.has("keyId"),"quarantine metadata only");evidence.add("actual-HTTP/OPERATOR/status/pause/original-retry/strict-version/quarantine-redaction/encoded-path=PASSED");
 }
 static void actualVersionMatrix(org.springframework.context.ApplicationContext ctx,IProductService products,IProductSyncRepository store,IProductSyncService service,RocketMqSyncTransport transport)throws Exception{
  var conflict=products.create(fields("B权威原商品",SaleStatus.ON_SALE),"real-version-conflict");var original=store.event(conflict.sync().targetEventId());
  var envelope=(com.fasterxml.jackson.databind.node.ObjectNode)JSON.readTree(original.body());String preId=UUID.randomUUID().toString();envelope.put("eventId",preId);((com.fasterxml.jackson.databind.node.ObjectNode)envelope.path("payload")).put("goodsName","隔离A同版本预置冲突样本");byte[] bytes=new ContractCodec().encode(envelope);
  var pre=new SyncWork(preId,original.goodsId(),1,original.saleStatus(),new String(bytes,java.nio.charset.StandardCharsets.UTF_8),ContractCodec.sha256(bytes),"PENDING",0,0,0,null,"WAITING",false);
  transport.publish(pre);waitFor(() -> transport.query(pre).status().equals("PROCESSED"),45000,"actual isolated A preexisting version fixture");service.publishOne(original.eventId());
  waitFor(() -> store.event(original.eventId()).processingState().equals("REJECTED"),45000,"actual A same-version different-content business rejection");
  check(store.claim("SEND",original.eventId(),30000)==null && products.detail(original.goodsId(),true).product().fields().goodsName().equals("B权威原商品"),"business refusal keeps B authority and stops resend");
  var repair=products.edit(original.goodsId(),1,fields("B权威修正版本2",SaleStatus.ON_SALE),"real-version-repair");service.publishOne(repair.sync().targetEventId());waitFor(() -> products.detail(original.goodsId(),true).sync().ready(2),45000,"new authoritative version repairs conflict");
  var first=products.create(fields("真实乱序版本1",SaleStatus.ON_SALE),"real-order");var second=products.edit(first.product().goodsId(),1,fields("真实乱序版本2",SaleStatus.ON_SALE),"real-order2");var third=products.edit(first.product().goodsId(),2,fields("真实乱序版本3",SaleStatus.OFF_SALE),"real-order3");
  service.publishOne(third.sync().targetEventId());waitFor(() -> products.detail(first.product().goodsId(),true).sync().ready(3),45000,"actual newest version confirms first");service.publishOne(first.sync().targetEventId());service.publishOne(second.sync().targetEventId());
  waitFor(() -> store.event(first.sync().targetEventId()).processingState().equals("RECONCILIATION_REQUIRED") && store.event(second.sync().targetEventId()).processingState().equals("RECONCILIATION_REQUIRED"),45000,"actual A ignores older facts with larger current version");check(products.detail(first.product().goodsId(),true).sync().ready(3),"old ignored results never regress newest confirmation");
  evidence.add("actual-A/same-version-conflict-REJECTED/no-resend/B-authority/new-version-repair/v3-before-v1-v2/IGNORED-larger-no-regression=PASSED");
 }
 static final class varFixtureProducer implements AutoCloseable {
  final org.apache.rocketmq.client.producer.DefaultMQProducer p;final MqSettings mq;
  varFixtureProducer(MqClientFactory f,MqSettings mq)throws Exception{this.mq=mq;p=f.producer("B_SYNC_TAG_TEST_"+UUID.randomUUID());p.start();}
  void sendWrongTag(SyncWork w)throws Exception{byte[] bytes=w.body().getBytes(java.nio.charset.StandardCharsets.UTF_8);var message=new org.apache.rocketmq.common.message.Message(mq.getProductTopic(),"UNMATCHED_TEST_TAG",w.eventId(),bytes);message.putUserProperty("keyId",mq.getBKeyId());message.putUserProperty("signature",ContractCodec.hmac(mq.getBSecret(),mq.getProductTopic()+"\n"+ContractCodec.sha256(bytes)));check(p.send(message,10000).getSendStatus()==org.apache.rocketmq.client.producer.SendStatus.SEND_OK,"real broker acknowledged unconsumed tag");}
  public void close(){p.shutdown();}
 }

}
