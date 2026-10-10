package cn.zj.zjmarket.verification;
import cn.zj.zjmarket.ZjMarketApplication;
import cn.zj.zjmarket.domain.identity.service.IIdentityService;
import cn.zj.zjmarket.domain.product.service.IProductService;
import cn.zj.zjmarket.domain.product.model.valobj.*;
import cn.zj.zjmarket.domain.inventory.service.IInventoryService;
import cn.zj.zjmarket.domain.inventory.model.valobj.InventoryRequest;
import cn.zj.zjmarket.domain.order.adapter.port.IPurchaseQuotePort;
import cn.zj.zjmarket.domain.order.adapter.repository.IOrderRepository;
import cn.zj.zjmarket.domain.order.model.valobj.PurchaseConditions;
import cn.zj.zjmarket.domain.order.service.IOrderService;
import cn.zj.zjmarket.domain.order.service.impl.OrderService;
import cn.zj.zjmarket.types.exception.OrderFailure;
import org.springframework.context.annotation.*;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.web.server.context.WebServerApplicationContext;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import javax.sql.DataSource;
import java.util.*;
import java.util.concurrent.*;
import java.nio.file.*;
import static cn.zj.zjmarket.verification.ProductCommands.*;
/** Actual B HTTP/MySQL; controlled quote port for deterministic failure races, never pretends to be A. */
public final class OrderCommands {
 static volatile CountDownLatch expiryQuote;
 @Configuration(proxyBeanMethods=false) public static class ProbeConfiguration {
  @Bean @Primary IPurchaseQuotePort controlledQuote(){return (user,q,request)->{check(!TransactionSynchronizationManager.isActualTransactionActive(),"network outside transaction");if(request.equals("expiry-wait")&&expiryQuote!=null)expiryQuote.countDown();if(!q.expectedOffer().payPrice().equals("9.00"))throw new OrderFailure(409,"OFFER_CHANGED");};}
 }
 public static int browserServer(){
  try{
   if(!env("B_DATABASE_SCOPE").equals("b02-test")||!env("B_DATABASE_USERNAME").equals("zj_market_b02_test_app")||!env("B_DATABASE_URL").matches("^jdbc:mysql://[^/]+/zj_market_b02_test(?:\\?.*)?$"))throw new IllegalArgumentException("Isolated B browser scope required");
   boolean withTrade="true".equals(System.getenv("B_BROWSER_TRADE"));var app=withTrade?new SpringApplication(ProbeConfiguration.class,TradeCommands.BrowserConfiguration.class,ZjMarketApplication.class):new SpringApplication(ProbeConfiguration.class,ZjMarketApplication.class);
   try(var ctx=app.run("--server.port=18092","--b.identity.enabled=true","--b.product.enabled=true","--b.inventory.enabled=true","--b.order.enabled=true","--b.trade.enabled="+withTrade,"--b.trade.scheduler-enabled=false","--b.trial.enabled=false","--b.sync.enabled=false","--b.infrastructure.database.enabled=true","--b.infrastructure.rpc.enabled=false","--b.infrastructure.mq.enabled=false")){
    var identity=ctx.getBean(IIdentityService.class);var operator=identity.login(env("B_BROWSER_OPERATOR_LOGIN_NAME"),env("B_BROWSER_OPERATOR_PASSWORD")).user();
    String goods=ctx.getBean(IProductService.class).create(new ProductFields("订单浏览器验收 "+UUID.randomUUID().toString().substring(0,8),"",null,"10.00","CNY",SaleStatus.ON_SALE),"order-browser").product().goodsId();ready(ctx.getBean(DataSource.class),goods);TradeCommands.browserGoods=goods;
    ctx.getBean(IInventoryService.class).execute(operator.userId(),UUID.randomUUID().toString(),new InventoryRequest("INBOUND",goods,10,1,"browser own fixture"));
    String exceptionId="";if(withTrade){var fixture=new TradeCommands(ctx,operator.userId(),operator.userId());var exception=fixture.create();var task=ctx.getBean(cn.zj.zjmarket.domain.order.adapter.repository.ITradeRepository.class);var send=task.beforeSend(task.claim(exception.orderId(),30000));task.complete(send,new cn.zj.zjmarket.domain.order.model.valobj.TradeReply("UPSTREAM_TIMEOUT",null));exceptionId=exception.orderId();}
    Files.createDirectories(Path.of("target/orders"));Files.writeString(Path.of("target/orders/browser-fixtures.json"),new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(Map.of("goodsId",goods,"offer",conditions(goods).expectedOffer(),"status","READY","exceptionOrderId",exceptionId)));
    long deadline=System.nanoTime()+TimeUnit.MINUTES.toNanos(5);while(System.nanoTime()<deadline){if(withTrade){var db=ctx.getBean(DataSource.class);var ids=new ArrayList<String>();try(var connection=db.getConnection();var ps=connection.prepareStatement("SELECT order_id FROM b_market_order WHERE goods_id=? AND business_status IN ('PROCESSING','CLOSING','WAITING_PAYMENT')")){ps.setString(1,goods);try(var rows=ps.executeQuery()){while(rows.next())ids.add(rows.getString(1));}}for(String id:ids)ctx.getBean(cn.zj.zjmarket.domain.order.service.ITradeCoordinationService.class).recover(id);}Thread.sleep(200);}
   }return 0;
  }catch(Exception e){System.err.println("Order browser fixture server failed: "+e.getClass().getSimpleName());return 1;}
 }
 public static int run(){
  try{
   if(!env("B_DATABASE_SCOPE").equals("b02-test")||!env("B_DATABASE_USERNAME").equals("zj_market_b02_test_app")||!env("B_DATABASE_URL").matches("^jdbc:mysql://[^/]+/zj_market_b02_test(?:\\?.*)?$"))throw new IllegalArgumentException("Exact isolated B scope required");
   var app=new SpringApplication(ProbeConfiguration.class,ZjMarketApplication.class);
   try(var ctx=app.run("--server.port=0","--b.identity.enabled=true","--b.product.enabled=true","--b.inventory.enabled=true","--b.order.enabled=true","--b.trade.enabled=false","--b.trial.enabled=false","--b.sync.enabled=false","--b.infrastructure.database.enabled=true","--b.infrastructure.rpc.enabled=false","--b.infrastructure.mq.enabled=false")){
    var db=ctx.getBean(DataSource.class);var identity=ctx.getBean(IIdentityService.class);var products=ctx.getBean(IProductService.class);var inventory=ctx.getBean(IInventoryService.class);var orders=ctx.getBean(IOrderService.class);var repo=ctx.getBean(IOrderRepository.class);
    String suffix=UUID.randomUUID().toString().replace("-","").substring(0,12),password="Order-"+UUID.randomUUID();
    var u=identity.register("orderu"+suffix,password,"order user");var v=identity.register("orderv"+suffix,password,"other user");var op=identity.initializeOperator("orderop"+suffix,password,"order operator");
    var http=new Client("http://127.0.0.1:"+((WebServerApplicationContext)ctx).getWebServer().getPort(),env("B_IDENTITY_ORIGIN"));String jwt=http.login("orderu"+suffix,password),other=http.login("orderv"+suffix,password);
    var fields=new ProductFields("Local order "+suffix,"",null,"10.00","CNY",SaleStatus.ON_SALE);
    String goods=products.create(fields,"order-acceptance").product().goodsId();ready(db,goods);inventory.execute(op.userId(),UUID.randomUUID().toString(),new InventoryRequest("INBOUND",goods,1,1,"order acceptance"));
    var q=conditions(goods);var input=Map.of("goodsId",goods,"mode","OPEN","expectedOffer",q.expectedOffer());
    for(String path:List.of("/orders","/orders/missing","/orders/by-intent/missing","/products/"+goods+"/active-order"))http.call("GET",path,null,null,401);
    http.call("POST","/purchase-confirmations",input,null,401);http.call("POST","/orders",Map.of("purchaseIntentId","missing","confirmationId","missing"),null,401);
    var extra=new HashMap<String,Object>(input);extra.put("userId",v.userId());http.call("POST","/purchase-confirmations",extra,jwt,400);http.call("GET","/orders?userId="+v.userId(),null,jwt,400);http.call("GET","/orders?page=0",null,jwt,400);
    String c1=http.call("POST","/purchase-confirmations",input,jwt,201).path("data").path("confirmationId").asText();String c2=http.call("POST","/purchase-confirmations",input,other,201).path("data").path("confirmationId").asText();
    http.call("POST","/orders",body("foreign",c1),other,404);
    String intent=UUID.randomUUID().toString(),otherIntent=UUID.randomUUID().toString();
    final String raceJwt=jwt,raceOther=other,raceC1=c1,raceC2=c2,raceIntent=intent,raceOtherIntent=otherIntent;
    try(var pool=Executors.newVirtualThreadPerTaskExecutor()){
     var a=pool.submit(()->http.send("POST","/orders",body(raceIntent,raceC1),raceJwt));var b=pool.submit(()->http.send("POST","/orders",body(raceOtherIntent,raceC2),raceOther));
     var ra=a.get();var rb=b.get();check(new HashSet<>(List.of(ra.statusCode(),rb.statusCode())).equals(Set.of(202,409)),"last unit only one accepted");
     if(rb.statusCode()==202){var tmp=jwt;jwt=other;other=tmp;var tu=u;u=v;v=tu;var tc=c1;c1=c2;c2=tc;var ti=intent;intent=otherIntent;otherIntent=ti;}
    }
    String order=http.call("GET","/orders/by-intent/"+intent,null,jwt,200).path("data").path("orderId").asText();
    check(inventory.detail(goods).available()==0 && inventory.detail(goods).reserved()==1,"account reservation exact");
    http.call("GET","/orders/"+order,null,other,404);http.call("GET","/orders/by-intent/"+intent,null,other,404);
    check(http.call("GET","/products/"+goods+"/active-order",null,jwt,200).path("data").path("orderId").asText().equals(order),"active purchase recovery");
    check(http.call("GET","/products/"+goods+"/active-order",null,other,200).path("data").isNull(),"other user active hidden");
    http.call("POST","/orders",body(intent,c1),jwt,200);http.call("POST","/orders",body(intent,c2),jwt,409);
    String c3=orders.confirm(u.userId(),q,"new-quote").confirmationId();http.call("POST","/orders",body(UUID.randomUUID().toString(),c3),jwt,409);
    // Deterministic same-key and different-key contention for one buyer on a new SKU.
    String same=products.create(fields,"same-key").product().goodsId();ready(db,same);inventory.execute(op.userId(),UUID.randomUUID().toString(),new InventoryRequest("INBOUND",same,3,1,"same key"));var sq=conditions(same);String sc=orders.confirm(u.userId(),sq,"quote").confirmationId(),si=UUID.randomUUID().toString();final String buyer=u.userId();
    try(var pool=Executors.newVirtualThreadPerTaskExecutor()){
     var a=pool.submit(()->orders.create(buyer,si,sc,"one"));var b=pool.submit(()->orders.create(buyer,si,sc,"two"));var x=a.get();var y=b.get();check(x.order().orderId().equals(y.order().orderId()) && x.replay()!=y.replay(),"same key concurrent replay");
    }
    check(inventory.detail(same).available()==2 && inventory.detail(same).reserved()==1,"same key only one reserve");
    // Different activities/teams and intent keys cannot bypass the per-user/SKU guard.
    String guardGoods=products.create(fields,"guard-race").product().goodsId();ready(db,guardGoods);inventory.execute(op.userId(),UUID.randomUUID().toString(),new InventoryRequest("INBOUND",guardGoods,3,1,"guard race"));
    var gq=conditions(guardGoods);String gc1=orders.confirm(buyer,gq,"open").confirmationId(),gc2=orders.confirm(buyer,new PurchaseConditions(guardGoods,"JOIN","candidate-team",gq.expectedOffer()),"join").confirmationId();
    try(var pool=Executors.newVirtualThreadPerTaskExecutor()){
     var a=pool.submit(()->createCode(orders,buyer,UUID.randomUUID().toString(),gc1));var b=pool.submit(()->createCode(orders,buyer,UUID.randomUUID().toString(),gc2));check(new HashSet<>(List.of(a.get(),b.get())).equals(Set.of("ACCEPTED","ACTIVE_PURCHASE_EXISTS")),"different intent OPEN/JOIN same SKU guard race");
    }
    check(inventory.detail(guardGoods).available()==2&&inventory.detail(guardGoods).reserved()==1,"guard race only one held unit");
    // Same intent on different SKUs hits the database unique key and rolls the loser back.
    String cross1=products.create(fields,"cross-one").product().goodsId(),cross2=products.create(fields,"cross-two").product().goodsId();
    for(String g:List.of(cross1,cross2)){ready(db,g);inventory.execute(op.userId(),UUID.randomUUID().toString(),new InventoryRequest("INBOUND",g,1,1,"cross key"));}
    String cc1=orders.confirm(buyer,conditions(cross1),"cross1").confirmationId(),cc2=orders.confirm(buyer,conditions(cross2),"cross2").confirmationId(),ci=UUID.randomUUID().toString();
    try(var pool=Executors.newVirtualThreadPerTaskExecutor()){
     var a=pool.submit(()->createCode(orders,buyer,ci,cc1));var b=pool.submit(()->createCode(orders,buyer,ci,cc2));check(new HashSet<>(List.of(a.get(),b.get())).equals(Set.of("ACCEPTED","IDEMPOTENCY_CONFLICT")),"cross-SKU intent unique race");
    }
    check(inventory.detail(cross1).reserved()+inventory.detail(cross2).reserved()==1&&inventory.detail(cross1).available()+inventory.detail(cross2).available()==1,"unique loser entire transaction rollback");
    // Fail after each write boundary, not only before the transaction starts.
    String rollbackGoods=products.create(fields,"rollback").product().goodsId();ready(db,rollbackGoods);inventory.execute(op.userId(),UUID.randomUUID().toString(),new InventoryRequest("INBOUND",rollbackGoods,5,1,"rollback"));var rq=conditions(rollbackGoods);
    String rc=orders.confirm(buyer,rq,"rollback-quote").confirmationId(),ri=UUID.randomUUID().toString();
    var proxy=(IOrderRepository)java.lang.reflect.Proxy.newProxyInstance(IOrderRepository.class.getClassLoader(),new Class[]{IOrderRepository.class},(obj,method,args)->{try{var result=method.invoke(repo,args);if(method.getName().equals("create"))throw new IllegalStateException("owned post-write fault");return result;}catch(java.lang.reflect.InvocationTargetException e){throw e.getCause();}});
    try{new OrderService(proxy,ctx.getBean(IPurchaseQuotePort.class),"s01","c01").create(buyer,ri,rc,"rollback");throw new IllegalStateException("check: expected rollback");}catch(IllegalStateException expected){check(!expected.getMessage().startsWith("check:"),"post-write rollback fault");}
    check(repo.byIntent(buyer,"s01","c01",ri)==null && repo.confirmation(rc,false).boundAt()==null && inventory.detail(rollbackGoods).available()==5 && inventory.detail(rollbackGoods).reserved()==0 && repo.active(buyer,rollbackGoods)==null,"all order facts rolled back");
    orders.create(buyer,ri,rc,"retry");check(inventory.detail(rollbackGoods).reserved()==1,"rollback confirmation reusable");
    // Simulate waiting on a product lock across the 5-minute expiry boundary.
    String expGoods=products.create(fields,"expiry").product().goodsId();ready(db,expGoods);inventory.execute(op.userId(),UUID.randomUUID().toString(),new InventoryRequest("INBOUND",expGoods,1,1,"expiry"));var eq=conditions(expGoods);String ec=orders.confirm(buyer,eq,"expiry").confirmationId();
    try(var connection=db.getConnection()){
     try(var statement=connection.prepareStatement("UPDATE b_purchase_confirmation SET issued_at_ms=issued_at_ms-299000,expires_at_ms=issued_at_ms+300000,snapshot=JSON_SET(snapshot,'$.issuedAt',issued_at_ms,'$.expiresAt',issued_at_ms+300000) WHERE confirmation_id=?")){statement.setString(1,ec);statement.executeUpdate();}
     connection.setAutoCommit(false);try(var lock=connection.prepareStatement("SELECT goods_id FROM b_product WHERE goods_id=? FOR UPDATE")){lock.setString(1,expGoods);lock.executeQuery().close();}
     try(var pool=Executors.newVirtualThreadPerTaskExecutor()){
      expiryQuote=new CountDownLatch(1);
      var waiting=pool.submit(()->{try{orders.create(buyer,UUID.randomUUID().toString(),ec,"expiry-wait");return "ACCEPTED";}catch(OrderFailure e){return e.code();}});
      check(expiryQuote.await(5,TimeUnit.SECONDS),"expiry quote reached before product lock");Thread.sleep(200);check(!waiting.isDone(),"actual transaction waits on held product row");Thread.sleep(1400);connection.commit();check(waiting.get().equals("CONFIRMATION_EXPIRED"),"lock wait expiry checked after locks");
     }
    }
    check(inventory.detail(expGoods).available()==1&&repo.confirmation(ec,false).boundAt()==null,"expiry no partial reserve");
    // Replay still works after the accepted SKU is edited and taken off sale.
    var before=products.detail(goods,true).product();products.edit(goods,before.version(),new ProductFields("renamed","",null,"20.00","CNY",SaleStatus.OFF_SALE),"post-order");
    var replay=http.call("POST","/orders",body(intent,c1),jwt,200).path("data");check(replay.path("product").path("name").asText().equals(fields.goodsName())&&replay.path("offer").path("payPrice").asText().equals("9.00")&&!replay.path("paymentEnabled").asBoolean(),"immutable snapshot replay off sale");
    long orderCount=scalar(db,"SELECT COUNT(*) FROM b_market_order WHERE order_id=?",order);check(orderCount==1,"single order fact");
    long configuredWait=ctx.getEnvironment().getProperty("b.order.reserve-wait-millis",Long.class,300000L);
    check(scalar(db,"SELECT reserve_wait_deadline_ms-created_at_ms FROM b_market_order WHERE order_id=?",order)==configuredWait,"configured D6 persisted through real HTTP and Spring wiring");
    check(scalar(db,"SELECT c.expires_at_ms-c.issued_at_ms FROM b_purchase_confirmation c JOIN b_market_order o ON o.confirmation_id=c.confirmation_id WHERE o.order_id=?",order)==300000L,"D9 remains independent of configurable D6");
    check(scalar(db,"SELECT COUNT(*) FROM b_inventory_reservation WHERE order_id=? AND state='HELD'",order)==1 && scalar(db,"SELECT COUNT(*) FROM b_trade_coordination WHERE order_id=? AND intent='RESERVE' AND run_state='READY' AND attempt_count=0",order)==1,"durable held and unsent task");
    var ledger=http.call("GET","/admin/inventory/"+goods+"/ledger",null,http.login("orderop"+suffix,password),200).path("data").path("items");check(ledger.size()==2,"operator and order ledgers visible");
    check(scalar(db,"SELECT COUNT(*) FROM b_market_order WHERE order_id=? AND may_have_dispatched=0 AND payment_exposure='NEVER_OPENED'",order)==1,"no A reserve/payment side effects");
    Path report=Path.of(env("B_ORDER_REPORT"));Files.createDirectories(report.toAbsolutePath().getParent());Files.write(report,List.of("status=PASSED","java="+Runtime.version(),"actualB=6 HTTP operations / MySQL V7 / permissions and owner isolation","atomic=order + bound confirmation + guard + held reservation + balance + ledger + ready task","concurrency=last unit / same-key replay / same-SKU OPEN-JOIN guard / cross-SKU unique loser rollback","failures=post-write rollback / lock wait past expiry / stock insufficient","recovery=original intent / active purchase / replay after off-sale / immutable snapshot","quote=controlled port, checks network outside local transaction; not real A acceptance","D6=configured wait persisted="+configuredWait+"ms / D9=300000ms unchanged","sideEffects=no A reserve, no payment"));
    System.out.println("B local order actual HTTP/MySQL acceptance: PASSED");
   }return 0;
  }catch(Exception e){System.err.println("B local order acceptance failed: "+e.getClass().getSimpleName()+" "+(e.getMessage()!=null&&e.getMessage().startsWith("check:")?e.getMessage():"details withheld"));try{Files.createDirectories(Path.of("target/orders"));Files.writeString(Path.of("target/orders/failure.txt"),e.toString());}catch(Exception ignored){}return 1;}
 }
 private static String createCode(IOrderService orders,String user,String intent,String confirmation){try{orders.create(user,intent,confirmation,"race");return "ACCEPTED";}catch(OrderFailure e){return e.code();}}
 private static Map<String,Object> body(String intent,String confirmation){return Map.of("purchaseIntentId",intent,"confirmationId",confirmation);}
 private static PurchaseConditions conditions(String goods){return new PurchaseConditions(goods,"OPEN",null,new TrialOffer("1",goods,"1","10.00","1.00","9.00","CNY",2));}
 private static void ready(DataSource db,String goods)throws Exception{try(var c=db.getConnection();var p=c.prepareStatement("UPDATE b_product_sync SET confirmed_version=target_version,state='CONFIRMED' WHERE goods_id=?")){p.setString(1,goods);check(p.executeUpdate()==1,"owned fixture sync");}}
 private static long scalar(DataSource db,String sql,String id)throws Exception{try(var c=db.getConnection();var p=c.prepareStatement(sql)){p.setString(1,id);try(var r=p.executeQuery()){r.next();return r.getLong(1);}}}
}
