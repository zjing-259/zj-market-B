package cn.zj.zjmarket.verification;

import cn.zj.zjmarket.ZjMarketApplication;
import cn.zj.zjmarket.domain.identity.service.IIdentityService;
import cn.zj.zjmarket.domain.order.adapter.port.ITradePort;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
import cn.zj.zjmarket.domain.order.model.valobj.*;
import cn.zj.zjmarket.domain.order.service.*;
import cn.zj.zjmarket.domain.payment.adapter.repository.*;
import cn.zj.zjmarket.domain.payment.adapter.port.*;
import cn.zj.zjmarket.domain.payment.model.valobj.*;
import cn.zj.zjmarket.domain.payment.service.IPaymentService;
import cn.zj.zjmarket.domain.payment.service.impl.PaymentService;
import cn.zj.zjmarket.types.exception.OrderFailure;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.web.server.context.WebServerApplicationContext;
import org.springframework.context.annotation.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.support.*;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import com.fasterxml.jackson.databind.*;
import javax.sql.DataSource;
import java.net.*;
import java.net.http.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import static cn.zj.zjmarket.verification.ProductCommands.*;

/** Isolated verification only: deterministic A/time failures, real B HTTP/MySQL/channel transactions. */
public final class PaymentCommands {
 private static final ObjectMapper JSON=new ObjectMapper();
 static volatile boolean offline;
 // Verification-only short frozen A window; ordinary payment configuration is unaffected.
 static volatile long fixtureWindowMs=900000;
 @Configuration(proxyBeanMethods=false) public static class ProbeConfiguration {
  @Bean @Primary ITradePort paymentProbe(DataSource source){var db=new JdbcTemplate(source);return new ITradePort(){public TradeReply execute(TradeDispatch d){
   check(!TransactionSynchronizationManager.isActualTransactionActive(),"A call outside market/channel transaction");if(offline)throw new OrderFailure(503,"OWNED_A_OFFLINE");
   long now=db.queryForObject("SELECT CAST(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3))*1000 AS SIGNED)",Long.class);
   var e=d.order().evidence();if(e==null){var c=d.order().confirmation();var q=c.conditions();e=new ReservationEvidence("RESERVATION","a-"+d.order().orderId(),d.order().orderId(),c.userId(),c.source(),c.channel(),"1",q.goodsId(),"1",1,"team-"+d.order().orderId(),"10.00","1.00","9.00","CNY",PaymentService.time(now-5000),PaymentService.time(now+fixtureWindowMs),"RESERVED","FORMING","1","1",PaymentService.time(now),null,false,false);}
   var fields=JSON.convertValue(e,new com.fasterxml.jackson.core.type.TypeReference<Map<String,Object>>(){});fields.put("serverTime",PaymentService.time(now));return new TradeReply("0000",JSON.convertValue(fields,ReservationEvidence.class));
  }public TeamView team(String user,String team,String request){throw new UnsupportedOperationException();}};}
 }
 private static String id(){return UUID.randomUUID().toString();}
 private static Map<String,Object> createBody(String key,String previous){var b=new LinkedHashMap<String,Object>();b.put("operationId",key);b.put("previousAttemptId",previous);return b;}
 private static HttpResponse<String> send(Client http,String path,String raw,String jwt,String origin)throws Exception{var builder=HttpRequest.newBuilder(URI.create(http.base+"/api/v1"+path)).timeout(java.time.Duration.ofSeconds(20)).header("Authorization","Bearer "+jwt).header("Content-Type","application/json");if(origin!=null)builder.header("Origin",origin);return http.http.send(builder.POST(HttpRequest.BodyPublishers.ofString(raw)).build(),HttpResponse.BodyHandlers.ofString());}
 private static JsonNode post(Client http,String path,Object body,String jwt,int status)throws Exception{var response=send(http,path,JSON.writeValueAsString(body),jwt,http.origin);check(response.statusCode()==status,"payment HTTP "+response.statusCode()+" expected "+status+" code="+JSON.readTree(response.body()).path("code").asText());check(response.headers().firstValue("Cache-Control").orElse("").contains("no-store"),"no-store");var result=JSON.readTree(response.body());check(response.headers().firstValue("X-Request-Id").orElse("").equals(result.path("requestId").asText()),"request trace");return result.path("data");}
 static MarketOrder fresh(org.springframework.context.ConfigurableApplicationContext ctx,String actor,String op)throws Exception{var fixture=new TradeCommands(ctx,actor,op);var o=fixture.create();ctx.getBean(ITradeCoordinationService.class).recover(o.orderId());o=ctx.getBean(IOrderService.class).detail(actor,o.orderId());check(o.businessStatus().equals("WAITING_PAYMENT"),"owned reserved order");return o;}
 public static int run(String mode){try{
  check(Set.of("verify","recover","browser","settlement-browser").contains(mode),"known payment verification mode");
  check(env("B_DATABASE_SCOPE").equals("b02-test")&&env("B_DATABASE_USERNAME").equals("zj_market_b02_test_app")&&env("B_DATABASE_URL").matches("^jdbc:mysql://[^/]+/zj_market_b02_test(?:\\?.*)?$"),"exact isolated test database");
  Path work=Path.of(env("B_PAYMENT_WORK"));Files.createDirectories(work);offline=mode.equals("recover");
  var app=new SpringApplication(ProbeConfiguration.class,OrderCommands.ProbeConfiguration.class,ZjMarketApplication.class);
  try(var ctx=app.run("--server.port="+(mode.endsWith("browser")?"18092":"0"),"--b.identity.enabled=true","--b.product.enabled=true","--b.inventory.enabled=true","--b.order.enabled=true","--b.trade.enabled=true","--b.trade.scheduler-enabled=false","--b.payment.enabled=true","--b.payment.checkout-enabled="+!mode.equals("recover"),"--b.payment.scheduler-enabled="+mode.endsWith("browser"),"--b.trade.events-enabled=false","--b.trial.enabled=false","--b.sync.enabled=false","--b.infrastructure.database.enabled=true","--b.infrastructure.rpc.enabled=false","--b.infrastructure.mq.enabled=false")){
   var service=ctx.getBean(IPaymentService.class);var repo=ctx.getBean(IPaymentRepository.class);var channel=ctx.getBean(ISimulatedChannel.class);var source=ctx.getBean(DataSource.class);var db=new JdbcTemplate(source);
   if(mode.equals("recover")){var fixture=JSON.readTree(Files.readString(work.resolve("restart.json")));String actor=fixture.path("actor").asText(),payment=fixture.path("payment").asText(),attempt=fixture.path("attempt").asText(),key=fixture.path("key").asText(),order=fixture.path("order").asText();var before=channel.query(payment,attempt);check(before.state().equals("SUCCEEDED"),"known paid channel persisted across JVM");
    // Owned expired lease simulates the process that died after the independently committed channel write.
    db.update("UPDATE b_payment_task SET lease_until_ms=0,next_attempt_ms=0 WHERE payment_id=? AND lease_token=?",payment,fixture.path("token").asText());
    service.tick(100);check(repo.attempt(payment,attempt).state().equals("SUCCEEDED"),"new JVM recovers existing success without A while checkout is disabled");check(repo.payment(actor,payment).fundsState().equals("UNKNOWN")&&repo.payment(actor,payment).successAttemptId()==null,"market success deferred until transactional outbox in .3");check(repo.operation(actor,key).progress().equals("APPLIED"),"original operation converges");check(db.queryForObject("SELECT COUNT(*) FROM b_inventory_ledger WHERE order_id=? AND kind IN ('RELEASE','CONFIRM')",Long.class,order)==0,"restart never releases or confirms");check(channel.query(payment,attempt).paidAt().equals(before.paidAt()),"immutable database paidAt across JVM");
    Files.writeString(work.resolve("recover.txt"),"status=PASSED\nnew-JVM/checkout-disabled/A-offline/original-attempt/immutable-paidAt/HELD=PASSED\n");return 0;
   }
   var identity=ctx.getBean(IIdentityService.class);String suffix=id().replace("-","").substring(0,10),password="Payment-"+id();var user=identity.register("payu"+suffix,password,"payment user");var other=identity.register("payv"+suffix,password,"other payment user");var op=identity.initializeOperator("payop"+suffix,password,"payment operator");var http=new Client("http://127.0.0.1:"+((WebServerApplicationContext)ctx).getWebServer().getPort(),env("B_IDENTITY_ORIGIN"));String jwt=http.login("payu"+suffix,password),foreign=http.login("payv"+suffix,password);
   var order=fresh(ctx,user.userId(),op.userId());String path="/orders/"+order.orderId()+"/payment",create="/orders/"+order.orderId()+"/payment-attempts";
   if(mode.endsWith("browser")){var manifest=new LinkedHashMap<String,Object>();manifest.put("orderId",order.orderId());manifest.put("loginName","payu"+suffix);manifest.put("otherLoginName","payv"+suffix);manifest.put("password",password);manifest.put("actor",user.userId());Files.writeString(work.resolve("browser-private.json"),JSON.writeValueAsString(manifest));Files.writeString(work.resolve("browser-ready.txt"),"READY");long deadline=System.nanoTime()+TimeUnit.MINUTES.toNanos(6);while(System.nanoTime()<deadline&&!Files.exists(work.resolve("browser-stop.txt"))){if(mode.equals("settlement-browser")){SettlementCommands.browserTick(ctx,work,user.userId(),order.orderId());FulfillmentCommands.browserTick(ctx,work,user.userId(),order.orderId());}Thread.sleep(250);}return 0;}
   http.call("GET",path,null,null,401);http.call("GET",path,null,foreign,404);check(http.call("GET",path,null,jwt,200).path("data").path("payment").isNull(),"GET never creates payment");http.call("GET",path+"?userId=foreign",null,jwt,400);
   check(send(http,create,JSON.writeValueAsString(createBody(id(),null)),jwt,null).statusCode()==403,"missing Origin rejected");check(send(http,create,JSON.writeValueAsString(createBody(id(),null)),jwt,"https://foreign.test").statusCode()==403,"foreign Origin rejected");
   post(http,create,Map.of("operationId",id()),jwt,400);post(http,create,Map.of("operationId",id(),"previousAttemptId","none","amount","0.01"),jwt,400);
   check(send(http,create,"{\"operationId\":\"first\",\"operationId\":\"second\",\"previousAttemptId\":null}",jwt,http.origin).statusCode()==400,"duplicate JSON rejected");
   String key=id();var body=createBody(key,null);JsonNode receipt;
   try(var pool=Executors.newVirtualThreadPerTaskExecutor()){var a=pool.submit(()->send(http,create,JSON.writeValueAsString(body),jwt,http.origin));var b=pool.submit(()->send(http,create,JSON.writeValueAsString(body),jwt,http.origin));var x=a.get();var y=b.get();check(new HashSet<>(List.of(x.statusCode(),y.statusCode())).equals(Set.of(200,202)),"same key concurrent create replay");receipt=JSON.readTree(x.body()).path("data");check(receipt.equals(JSON.readTree(y.body()).path("data")),"immutable receipt");}
   String payment=receipt.path("paymentId").asText(),attempt=receipt.path("attemptId").asText();check(repo.order(user.userId(),order.orderId()).paymentExposure().equals("POSSIBLY_OPENED")&&channel.query(payment,attempt)==null,"market intent exposed before independent channel creation");
   http.call("GET","/payments/"+payment,null,foreign,404);http.call("GET","/payments/"+payment+"/attempts/"+attempt,null,foreign,404);post(http,create,createBody(key,"different"),jwt,409);
   offline=true;try{check(post(http,create,body,jwt,200).equals(receipt),"original response-loss replay bypasses A outage");}finally{offline=false;}
   post(http,create,createBody(id(),null),jwt,409);check(db.queryForObject("SELECT COUNT(*) FROM b_payment_attempt WHERE payment_id=?",Long.class,payment)==1,"no extra active attempt");service.tick(100);check(channel.query(payment,attempt).state().equals("OPEN")&&repo.attempt(payment,attempt).state().equals("OPEN"),"durable channel create");
   var tx=new TransactionTemplate(new DataSourceTransactionManager(source));try{tx.executeWithoutResult(s->channel.query(payment,attempt));throw new IllegalStateException("check: outer transaction accepted");}catch(IllegalStateException expected){check(!expected.getMessage().startsWith("check:"),"channel rejects ambient transaction");}

   tx.executeWithoutResult(status->{db.update("UPDATE b_payment_operation SET receipt_json=JSON_SET(receipt_json,'$.receivedAt',0) WHERE actor_id=? AND operation_key=?",user.userId(),key);try{repo.operation(user.userId(),key);throw new IllegalStateException("check: receipt corruption accepted");}catch(IllegalStateException expected){check(expected.getMessage().equals("Payment receipt audit mismatch"),"immutable receipt hash verified");}status.setRollbackOnly();});check(repo.operation(user.userId(),key).receipt().receivedAt()>0,"receipt fault probe rolled back");
   String choose="/payments/"+payment+"/attempts/"+attempt+"/simulated-results",choice=id();post(http,choose,Map.of("operationId",choice,"result","FAILED"),jwt,202);
   offline=true;try{service.tick(100);check(repo.attempt(payment,attempt).state().equals("UNKNOWN")&&channel.query(payment,attempt).state().equals("OPEN"),"A outage before channel choice remains UNKNOWN");post(http,choose,Map.of("operationId",choice,"result","FAILED"),jwt,200);}finally{offline=false;}
   post(http,create,createBody(id(),attempt),jwt,409);post(http,choose,Map.of("operationId",id(),"result","FAILED"),jwt,202);db.update("UPDATE b_payment_task SET next_attempt_ms=0 WHERE payment_id=? AND state='WAITING_DEPENDENCY'",payment);
   post(http,choose,Map.of("operationId",id(),"result","SUCCEEDED"),jwt,409);service.tick(100);check(repo.attempt(payment,attempt).state().equals("FAILED")&&repo.payment(user.userId(),payment).fundsState().equals("UNPAID"),"failure ends attempt only");post(http,choose,Map.of("operationId",id(),"result","FAILED"),jwt,200);check(db.queryForObject("SELECT state FROM b_inventory_reservation WHERE order_id=?",String.class,order.orderId()).equals("HELD"),"failure keeps inventory");
   post(http,create,createBody(id(),null),jwt,409);var second=post(http,create,createBody(id(),attempt),jwt,202);String retry=second.path("attemptId").asText();check(second.path("paymentId").asText().equals(payment),"retry uses stable market payment");service.tick(100);
   String choose2="/payments/"+payment+"/attempts/"+retry+"/simulated-results",successKey=id();post(http,choose2,Map.of("operationId",successKey,"result","SUCCEEDED"),jwt,202);
   Work workItem=repo.claim(payment);check(workItem!=null,"owned work claimed");var current=repo.order(user.userId(),order.orderId());long now=repo.now();var fresh=ctx.getBean(ITradePort.class).execute(new TradeDispatch(null,current,"query",id(),null)).evidence();var time=new Evidence(fresh,now,repo.now(),1000000,2000,2000,2000);channel.choose(repo.payment(user.userId(),payment),repo.attempt(payment,retry),current,time,"SUCCEEDED");
   check(repo.attempt(payment,retry).state().equals("UNKNOWN")&&channel.query(payment,retry).state().equals("SUCCEEDED"),"channel committed independently before market projection");
   check(send(http,"/orders/"+order.orderId()+"/cancel",JSON.writeValueAsString(Map.of("operationId",id(),"reason","owned payment protection")),jwt,http.origin).statusCode()==409,"legacy cancel refuses exposed order");
   check(db.queryForObject("SELECT COUNT(*) FROM b_sim_attempt WHERE payment_id=? AND state='SUCCEEDED'",Long.class,payment)==1,"single channel success");check(db.queryForObject("SELECT COUNT(*) FROM b_sim_notification WHERE payment_id=?",Long.class,payment)==2,"each terminal attempt has durable notification");

   try{channel.choose(repo.payment(user.userId(),payment),repo.attempt(payment,retry),current,time,"FAILED");throw new IllegalStateException("check: successful channel reversed");}catch(OrderFailure expected){check(expected.code().equals("PAYMENT_RESULT_CONFLICT"),"success never reverses");}
   try{db.update("UPDATE b_sim_attempt SET state='SUCCEEDED',paid_at_ms=? WHERE payment_id=? AND attempt_id=?",repo.now(),payment,attempt);throw new IllegalStateException("check: second success allowed");}catch(org.springframework.dao.DuplicateKeyException expected){check(channel.query(payment,attempt).state().equals("FAILED"),"generated success uniqueness rejects second success atomically");}
   // A separate owned order proves opposite choices race with real transactions, independent of scheduling order.
   var raced=fresh(ctx,user.userId(),op.userId());String raceCreate="/orders/"+raced.orderId()+"/payment-attempts";JsonNode racedReceipt;
   try(var pool=Executors.newVirtualThreadPerTaskExecutor()){var a=pool.submit(()->send(http,raceCreate,JSON.writeValueAsString(createBody(id(),null)),jwt,http.origin));var b=pool.submit(()->send(http,raceCreate,JSON.writeValueAsString(createBody(id(),null)),jwt,http.origin));var x=a.get();var y=b.get();check(new HashSet<>(List.of(x.statusCode(),y.statusCode())).equals(Set.of(202,409)),"different key create race opens one attempt");racedReceipt=JSON.readTree(x.statusCode()==202?x.body():y.body()).path("data");}
   String rp=racedReceipt.path("paymentId").asText(),ra=racedReceipt.path("attemptId").asText();service.tick(100);String raceResult="/payments/"+rp+"/attempts/"+ra+"/simulated-results";
   try(var pool=Executors.newVirtualThreadPerTaskExecutor()){var a=pool.submit(()->send(http,raceResult,JSON.writeValueAsString(Map.of("operationId",id(),"result","SUCCEEDED")),jwt,http.origin));var b=pool.submit(()->send(http,raceResult,JSON.writeValueAsString(Map.of("operationId",id(),"result","FAILED")),jwt,http.origin));check(new HashSet<>(List.of(a.get().statusCode(),b.get().statusCode())).equals(Set.of(202,409)),"opposite result race accepts exactly one choice");}
   service.tick(100);check(Set.of("FAILED","SUCCEEDED").contains(channel.query(rp,ra).state())&&db.queryForObject("SELECT COUNT(*) FROM b_sim_notification WHERE payment_id=?",Long.class,rp)==1,"race yields exactly one terminal notification");
   check(db.queryForObject("SELECT COUNT(*) FROM b_inventory_ledger WHERE order_id=? AND kind IN ('RELEASE','CONFIRM')",Long.class,raced.orderId())==0,"raced payment retains stock");

   var leaseOrder=fresh(ctx,user.userId(),op.userId());var leaseAccepted=service.create(user.userId(),leaseOrder.orderId(),id(),null,id());String lp=leaseAccepted.receipt().paymentId(),la=leaseAccepted.receipt().attemptId();var abandoned=repo.claim(lp);check(abandoned!=null,"owned lease claimed");var lo=repo.order(user.userId(),leaseOrder.orderId());long t0=repo.now();var le=ctx.getBean(ITradePort.class).execute(new TradeDispatch(null,lo,"query",id(),null)).evidence();var createdChannel=channel.create(repo.payment(user.userId(),lp),repo.attempt(lp,la),lo,new Evidence(le,t0,repo.now(),1000000,2000,2000,2000));
   db.update("UPDATE b_payment_task SET lease_until_ms=? WHERE payment_id=? AND lease_token=?",repo.now()+150,lp,abandoned.token());
   try(var connection=source.getConnection()){connection.setAutoCommit(false);try(var statement=connection.prepareStatement("SELECT goods_id FROM b_product WHERE goods_id=? FOR UPDATE")){statement.setString(1,lo.confirmation().conditions().goodsId());statement.executeQuery().close();}try(var pool=Executors.newVirtualThreadPerTaskExecutor()){var blocked=pool.submit(()->repo.finish(abandoned,createdChannel));Thread.sleep(80);check(!blocked.isDone(),"real market lock blocks completion");Thread.sleep(250);connection.commit();blocked.get(5,TimeUnit.SECONDS);}}
   check(repo.attempt(lp,la).state().equals("CREATING"),"lease checked after lock wait; stale worker cannot project");db.update("UPDATE b_payment_task SET next_attempt_ms=0 WHERE payment_id=?",lp);var replacement=repo.claim(lp);check(replacement!=null&&!replacement.token().equals(abandoned.token()),"expired work reclaimed with new token");repo.finish(replacement,createdChannel);long version=repo.attempt(lp,la).version();repo.finish(abandoned,createdChannel);check(repo.attempt(lp,la).state().equals("OPEN")&&repo.attempt(lp,la).version()==version,"recovered projection and stale completion fenced");

   var samples=new LinkedHashMap<String,Object>();samples.put("OrderPaymentViewResponse",http.call("GET",path,null,jwt,200));samples.put("PaymentViewResponse",http.call("GET","/payments/"+payment,null,jwt,200));samples.put("AttemptViewResponse",http.call("GET","/payments/"+payment+"/attempts/"+retry,null,jwt,200));samples.put("OperationViewResponse",http.call("GET","/orders/"+order.orderId()+"/payment-operations/"+key,null,jwt,200));samples.put("OperationReceiptResponse",JSON.readTree(send(http,create,JSON.writeValueAsString(body),jwt,http.origin).body()));samples.put("choose-result",JSON.readTree(send(http,choose,JSON.writeValueAsString(Map.of("operationId",choice,"result","FAILED")),jwt,http.origin).body()));samples.put("Error",http.call("GET",path,null,"invalid-token",401));Files.writeString(work.resolve("http-contract-samples.json"),JSON.writeValueAsString(samples));
   var manifest=Map.of("actor",user.userId(),"order",order.orderId(),"payment",payment,"attempt",retry,"key",successKey,"token",workItem.token());Files.writeString(work.resolve("restart.json"),JSON.writeValueAsString(manifest));
   Files.writeString(work.resolve("verify.txt"),"status=PASSED\nreal-HTTP/MySQL/independent-channel=PASSED\ncontrolled-A-only;actual-A-evidence-is-separate\nowner/auth/origin/strict-body/no-store/requestId/GET-no-write=PASSED\nsame-key-race/response-loss/A-outage-replay/active-attempt/predecessor/retry-stable-payment=PASSED\nfailure-keeps-HELD/opposite-choice-race/one-success-DB-constraint/terminal-notifications/legacy-close-protection=PASSED\nUNKNOWN-outage/original-choice/same-choice-binding/receipt-hash/actual-lock-wait/expired-lease/stale-completion=PASSED\nrestart=PREPARED\n");return 0;
  }
 }catch(Exception e){System.err.println("Payment verification failed: "+e.getClass().getSimpleName()+" "+(e.getMessage()!=null&&e.getMessage().startsWith("check:")?e.getMessage():"details withheld"));return 1;}}
}
