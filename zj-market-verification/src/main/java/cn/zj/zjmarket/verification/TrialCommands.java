package cn.zj.zjmarket.verification;
import cn.zj.zjmarket.ZjMarketApplication;
import cn.zj.zjmarket.application.product.*;
import cn.zj.zjmarket.application.identity.*;
import cn.zj.zjmarket.domain.product.*;
import cn.zj.zjmarket.infrastructure.product.*;
import cn.zj.zjmarket.infrastructure.config.RpcSettings;
import cn.zj.zjmarket.infrastructure.integration.codec.ContractCodec;
import cn.zj.zjmarket.infrastructure.integration.rpc.RpcClientFactory;
import org.springframework.boot.*;
import org.springframework.context.annotation.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.web.server.context.WebServerApplicationContext;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import com.fasterxml.jackson.databind.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
/** Actual B HTTP/MySQL and A TLS/MQ acceptance, exclusively isolated learning schemas. */
public final class TrialCommands {
 static final ObjectMapper JSON=new ObjectMapper();
 public static int run(String mode){try{
  if(!Set.of("prepare","verify","offline").contains(mode))throw new IllegalArgumentException("Unsupported trial verification phase");SyncCommands.guard();
  boolean live=mode.equals("verify"),prepare=mode.equals("prepare");
  var app=new SpringApplication(ZjMarketApplication.class,ProbeConfiguration.class);if(prepare)app.setWebApplicationType(WebApplicationType.NONE);
  try(var ctx=app.run("--server.port=0","--b.identity.enabled=true","--b.product.enabled=true","--b.trial.enabled="+!prepare,"--b.sync.enabled="+live,"--b.sync.scheduler-enabled=false","--b.infrastructure.database.enabled=true","--b.infrastructure.rpc.enabled="+!prepare,"--b.infrastructure.mq.enabled="+live)){
   var work=Path.of(SyncCommands.env("B_TRIAL_WORK"));Files.createDirectories(work);var manifest=work.resolve("fixtures.json");var products=ctx.getBean(ProductService.class);var identity=ctx.getBean(IdentityService.class);
   if(prepare){
    SyncCommands.check(!Files.exists(manifest),"new owned fixture manifest only");var user=identity.register(env("LOGIN_NAME"),env("PASSWORD"),"trial user");var member=identity.register(env("MEMBER_LOGIN_NAME"),env("MEMBER_PASSWORD"),"trial member");var op=identity.initializeOperator(env("OP_LOGIN_NAME"),env("OP_PASSWORD"),"trial operator");
    var fixtures=new LinkedHashMap<String,Object>();fixtures.put("userId",user.userId());fixtures.put("memberId",member.userId());fixtures.put("operatorId",op.userId());fixtures.put("discountId",Integer.toString(10000000+new java.security.SecureRandom().nextInt(90000000)));fixtures.put("tagId","b025-"+UUID.randomUUID().toString().replace("-","").substring(0,20));
    for(String key:List.of("public","ineligible","hidden","none","race")){
     var p=products.create(new Product.Fields("试算"+key+"-"+UUID.randomUUID().toString().substring(0,8),"实际A试算隔离样本",null,"100.00","CNY",Product.SaleStatus.ON_SALE),"b025");fixtures.put(key,Map.of("goodsId",p.product().goodsId(),"eventId",p.sync().targetEventId(),"goodsName",p.product().fields().goodsName(),"activityId",Long.toString(700000000000L+new java.security.SecureRandom().nextLong(100000000000L))));
    }
    Files.write(manifest,new ContractCodec().encode(fixtures));System.out.println("B trial owned fixtures prepared: PASSED");return 0;
   }
   var f=JSON.readTree(Files.readAllBytes(manifest));var evidence=new ArrayList<String>();var bridge=ctx.getBean(Bridge.class);String base="http://127.0.0.1:"+((WebServerApplicationContext)ctx).getWebServer().getPort();var http=new ProductCommands.Client(base,SyncCommands.env("B_IDENTITY_ORIGIN"));String user=http.login(env("LOGIN_NAME"),env("PASSWORD"));
   if(!live){var failed=http.call("POST",path(f,"public"),Map.of(),user,503);SyncCommands.check(failed.path("data").isNull() && failed.path("code").asText().equals("DEPENDENCY_UNAVAILABLE"),"A offline never successful no activity");Files.write(work.resolve("offline.txt"),List.of("status=PASSED","actual-A-provider-offline/B-startup+public-browse-remain-available/trial-503-not-NO_PUBLIC_OFFER=PASSED"));http.call("GET","/products",null,null,200);return 0;}
   String member=http.login(env("MEMBER_LOGIN_NAME"),env("MEMBER_PASSWORD")),operator=http.login(env("OP_LOGIN_NAME"),env("OP_PASSWORD"));var sync=ctx.getBean(ProductSyncService.class);var transport=ctx.getBean(RocketMqSyncTransport.class);
   transport.startConsumer(8,false);
   for(String key:List.of("public","ineligible","hidden","none","race")){
    var row=f.path(key);sync.publishOne(row.path("eventId").asText());SyncCommands.waitFor(() -> products.detail(row.path("goodsId").asText(),true).sync().ready(1),45000,"actual A snapshot acknowledged: "+key);
   }
   http.call("POST",path(f,"public"),Map.of(),null,401);http.call("POST",path(f,"public"),Map.of(),"invalid-token",401);
   for(String key:List.of("userId","productVersion","originalPrice","activityId","quantity","source","channel"))http.call("POST",path(f,"public"),Map.of(key,"forged"),user,400);
   http.call("POST",path(f,"public")+"?userId=forged",Map.of(),user,400);http.call("POST",path(f,"public"),null,user,400);http.call("POST",path(f,"public"),List.of(),user,400);http.call("POST",path(f,"public").replace("trial","%74rial"),Map.of(),null,401);
   var offer=http.call("POST",path(f,"public"),Map.of(),user,200).path("data");SyncCommands.check(offer.path("state").asText().equals("AVAILABLE") && offer.path("offer").path("payPrice").asText().equals("90.00") && offer.path("offer").path("deductionPrice").asText().equals("10.00"),"real A public offer");
   http.call("POST",path(f,"public"),Map.of(),operator,200);var repeat=http.send("POST",path(f,"public"),Map.of(),user);SyncCommands.check(repeat.headers().firstValue("Cache-Control").orElse("").equals("no-store"),"no browser cache");
   var restricted=http.call("POST",path(f,"ineligible"),Map.of(),user,200).path("data");SyncCommands.check(restricted.path("state").asText().equals("INELIGIBLE") && restricted.path("offer").path("payPrice").asText().equals("90.00"),"real visible but ineligible");
   for(String key:List.of("none","hidden")){var q=http.call("POST",path(f,key),Map.of(),user,200).path("data");SyncCommands.check(q.size()==5 && q.path("state").asText().equals("NO_PUBLIC_OFFER") && q.path("offer").isNull() && !q.has("reasonCode") && !q.has("activityId"),"no hidden offer or private reason leaked: "+key);}
   var qualified=http.call("POST",path(f,"hidden"),Map.of(),member,200).path("data");SyncCommands.check(qualified.path("state").asText().equals("AVAILABLE"),"actual B user ID qualifies only matching A crowd member");
   evidence.add("actual-A/TLS/fresh-signature-and-nonce/public-price/visible-ineligible/hidden-redaction/no-activity/member-specific-identity=PASSED");
   var pending=products.create(new Product.Fields("未同步不得试算",nullSafeDescription(),null,"100.00","CNY",Product.SaleStatus.ON_SALE),"b025-pending");int calls=bridge.calls.get();http.call("POST","/products/"+pending.product().goodsId()+"/trial",Map.of(),user,409);SyncCommands.check(bridge.calls.get()==calls,"pending never calls A");
   var off=products.create(new Product.Fields("本地下架",nullSafeDescription(),null,"100.00","CNY",Product.SaleStatus.OFF_SALE),"b025-off");http.call("POST","/products/"+off.product().goodsId()+"/trial",Map.of(),user,404);SyncCommands.check(bridge.calls.get()==calls,"off sale never calls A");
   faultMatrix(ctx,http,user,f,bridge);
   evidence.add("controlled-port-invalid-quote/hidden-populated-offer-redaction/typed-RPC-envelope-invalid-requestId-null-flags/actual-SDK-stalled-TLS-timeout-504=PASSED");
   var responseReturned=new CountDownLatch(1);var release=new CountDownLatch(1);bridge.after=q->{responseReturned.countDown();try{if(!release.await(20,TimeUnit.SECONDS))throw new IllegalStateException("check: release race");}catch(InterruptedException e){throw new RuntimeException(e);}};
   try(var executor=Executors.newSingleThreadExecutor()){
    var request=executor.submit(()->http.call("POST",path(f,"race"),Map.of(),user,409));SyncCommands.check(responseReturned.await(20,TimeUnit.SECONDS),"actual A replied before concurrent edit");
    var before=http.call("GET","/admin/products/"+f.path("race").path("goodsId").asText(),null,operator,200).path("data");var edit=ProductCommands.edit(before);edit.put("description","实际运营HTTP在途修改");http.call("PUT","/admin/products/"+f.path("race").path("goodsId").asText(),edit,operator,200);release.countDown();SyncCommands.check(request.get(20,TimeUnit.SECONDS).path("code").asText().equals("PRODUCT_VERSION_MISMATCH"),"old valid A price discarded after actual concurrent operator edit");
   }finally{release.countDown();bridge.after=null;}
   var newVersion=products.detail(f.path("race").path("goodsId").asText(),true);sync.publishOne(newVersion.sync().targetEventId());SyncCommands.waitFor(()->products.detail(newVersion.product().goodsId(),true).sync().ready(2),45000,"new version confirms for future trial");SyncCommands.check(http.call("POST",path(f,"race"),Map.of(),user,200).path("data").path("productVersion").asText().equals("2"),"fresh version trial");
   evidence.add("actual-HTTP/authentication/empty-body-only/encoded-route/USER+OPERATOR/no-store/local-pending-offline-boundary=PASSED");evidence.add("actual-A-result/concurrent-operator-HTTP-edit/no-transaction-during-RPC/stale-discard/new-version-retrial=PASSED");
   evidence.add("java="+Runtime.version());evidence.add("springBoot="+SpringBootVersion.getVersion());evidence.add("status=PASSED");Files.write(work.resolve("verify.txt"),evidence);System.out.println("B actual trial integration: PASSED");
  }return 0;
 }catch(Exception e){System.err.println("B trial verification failed: "+e.getClass().getSimpleName()+" "+(e.getMessage()!=null && e.getMessage().startsWith("check:")?e.getMessage():"details withheld"));return 1;}}
 static String nullSafeDescription(){return "";}
 static String env(String key){return SyncCommands.env("B_TRIAL_TEST_"+key);}
 static String path(JsonNode f,String key){return "/products/"+f.path(key).path("goodsId").asText()+"/trial";}
 static MarketingTrialPort.Quote good(Product p){return new MarketingTrialPort.Quote(true,true,true,java.time.format.DateTimeFormatter.ofPattern("uuuu-MM-dd'T'HH:mm:ss.SSS'Z'").withZone(java.time.ZoneOffset.UTC).format(java.time.Instant.now()),new MarketingTrialPort.Offer("123",p.goodsId(),Long.toString(p.version()),"100.00","10.00","90.00","CNY",3));}
 static void faultMatrix(org.springframework.context.ApplicationContext ctx,ProductCommands.Client http,String jwt,JsonNode f,Bridge bridge)throws Exception{
  var rpc=ctx.getBean(RpcSettings.class);var bad=copy(rpc);bad.setSecret("public-controlled-wrong-secret");
  try(var adapter=new DubboMarketingTrial(bad,new RpcClientFactory(bad))){bridge.target=adapter;SyncCommands.check(http.call("POST",path(f,"public"),Map.of(),jwt,502).path("code").asText().equals("INTEGRATION_AUTH_FAILED"),"real A bad integration signature is not browser 401");}finally{bridge.target=null;}
  for(String fault:List.of("flags","time","price","relation","goods","version","currency","target","missing")){
   bridge.target=(u,p,id)->{var q=good(p);var o=q.offer();switch(fault){case "flags":return new MarketingTrialPort.Quote(null,true,true,q.quotedAt(),o);case "time":return new MarketingTrialPort.Quote(true,true,true,"not-time",o);case "price":o=new MarketingTrialPort.Offer(o.activityId(),o.goodsId(),o.productVersion(),"99.00","10.00","89.00","CNY",3);break;case "relation":o=new MarketingTrialPort.Offer(o.activityId(),o.goodsId(),o.productVersion(),"100.00","10.00","89.00","CNY",3);break;case "goods":o=new MarketingTrialPort.Offer(o.activityId(),"other",o.productVersion(),"100.00","10.00","90.00","CNY",3);break;case "version":o=new MarketingTrialPort.Offer(o.activityId(),o.goodsId(),"2","100.00","10.00","90.00","CNY",3);break;case "currency":o=new MarketingTrialPort.Offer(o.activityId(),o.goodsId(),o.productVersion(),"100.00","10.00","90.00","USD",3);break;case "target":o=new MarketingTrialPort.Offer(o.activityId(),o.goodsId(),o.productVersion(),"100.00","10.00","90.00","CNY",0);break;default:o=null;}return new MarketingTrialPort.Quote(true,true,true,q.quotedAt(),o);};
   SyncCommands.check(http.call("POST",path(f,"public"),Map.of(),jwt,502).path("data").isNull(),"controlled bad quote rejected "+fault);
  }
  bridge.target=(u,p,id)->new MarketingTrialPort.Quote(true,false,true,good(p).quotedAt(),good(p).offer());SyncCommands.check(http.call("POST",path(f,"public"),Map.of(),jwt,200).path("data").path("offer").isNull(),"controlled hidden populated offer fully redacted");bridge.target=null;
  TrialRpcFaults.verify(ctx,http,jwt,f,bridge);
 }
 static RpcSettings copy(RpcSettings r){var c=new RpcSettings();c.setUrl(r.getUrl());c.setGroup(r.getGroup());c.setVersion(r.getVersion());c.setClientId(r.getClientId());c.setKeyId(r.getKeyId());c.setSecret(r.getSecret());c.setSource(r.getSource());c.setChannel(r.getChannel());c.setClientCertificate(r.getClientCertificate());c.setClientPrivateKey(r.getClientPrivateKey());c.setTrustCertificate(r.getTrustCertificate());c.setTimeoutMillis(r.getTimeoutMillis());return c;}
 static final class Bridge implements MarketingTrialPort{
  final MarketingTrialPort real;final AtomicInteger calls=new AtomicInteger();volatile MarketingTrialPort target;volatile java.util.function.Consumer<Quote> after;
  Bridge(MarketingTrialPort real){this.real=real;}
  public Quote trial(String u,Product p,String id){SyncCommands.check(!TransactionSynchronizationManager.isActualTransactionActive(),"RPC must be outside local transaction");calls.incrementAndGet();var q=(target==null?real:target).trial(u,p,id);if(after!=null)after.accept(q);return q;}
 }
 @Configuration(proxyBeanMethods=false) @ConditionalOnProperty(name="b.trial.enabled",havingValue="true")
 static class ProbeConfiguration{@Bean @Primary Bridge trialProbe(DubboMarketingTrial real){return new Bridge(real);}}
}
