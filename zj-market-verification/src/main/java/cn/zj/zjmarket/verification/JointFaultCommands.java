package cn.zj.zjmarket.verification;

import cn.zj.zjmarket.ZjMarketApplication;
import cn.zj.zjmarket.domain.identity.service.IIdentityService;
import cn.zj.zjmarket.domain.inventory.service.IInventoryService;
import cn.zj.zjmarket.domain.inventory.model.valobj.InventoryRequest;
import cn.zj.zjmarket.domain.order.adapter.repository.ITradeRepository;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
import cn.zj.zjmarket.domain.order.model.valobj.*;
import cn.zj.zjmarket.domain.order.service.*;
import cn.zj.zjmarket.domain.order.service.impl.TradeCoordinationService;
import cn.zj.zjmarket.types.exception.OrderFailure;
import org.springframework.boot.SpringApplication;
import org.springframework.context.ConfigurableApplicationContext;
import javax.sql.DataSource;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import static cn.zj.zjmarket.verification.ProductCommands.*;

/** Actual MySQL production services, verification-only remote fault port and owned fixtures. */
public final class JointFaultCommands {
    private final TradeCommands fixtures;
    private final ITradeRepository tasks;
    private final IOrderService orders;
    private final IOrderLifecycleService lifecycle;
    private final IInventoryService inventory;
    private final CloseCommands.Sim remote;
    private final DataSource db;
    private final String user, other, operator;
    private final Set<String> goods = new LinkedHashSet<>();
    private final List<String> checks = new ArrayList<>();

    private JointFaultCommands(ConfigurableApplicationContext ctx, String user, String other, String operator) {
        this.user=user; this.other=other; this.operator=operator;
        fixtures=new TradeCommands(ctx,user,operator);
        tasks=ctx.getBean(ITradeRepository.class); orders=ctx.getBean(IOrderService.class);
        lifecycle=ctx.getBean(IOrderLifecycleService.class); inventory=ctx.getBean(IInventoryService.class);
        remote=ctx.getBean(CloseCommands.Sim.class); db=ctx.getBean(DataSource.class);
    }
    private MarketOrder create() throws Exception {
        var o=fixtures.create(); goods.add(o.confirmation().conditions().goodsId()); return o;
    }
    private static String key(){return UUID.randomUUID().toString();}
    private static <T> List<T> race(List<Callable<T>> work) throws Exception {
        var ready=new CountDownLatch(work.size());var start=new CountDownLatch(1);
        try(var pool=Executors.newVirtualThreadPerTaskExecutor()){
            var futures=new ArrayList<Future<T>>();
            for(var call:work)futures.add(pool.submit(()->{ready.countDown();check(start.await(5,TimeUnit.SECONDS),"race start bounded");return call.call();}));
            check(ready.await(5,TimeUnit.SECONDS),"all competing tasks ready");start.countDown();
            var answers=new ArrayList<T>();for(var f:futures)answers.add(f.get(20,TimeUnit.SECONDS));return answers;
        } finally {start.countDown();}
    }
    private void settle(MarketOrder o) throws Exception {
        var worker=new TradeCoordinationService(tasks,remote,30000);
        for(int i=0;i<5&&!fixtures.get(o).businessStatus().equals("CLOSED");i++){fixtures.due(o);worker.recover(o.orderId());}
        check(fixtures.get(o).businessStatus().equals("CLOSED"),"closing converges");
        check(fixtures.count("SELECT COUNT(*) FROM b_inventory_ledger WHERE order_id=? AND kind='RELEASE'",o.orderId())==1,"one release per closed order");
        check(fixtures.count("SELECT COUNT(*) FROM b_purchase_guard WHERE active_order_id=?",o.orderId())==0,"closed guard cleared");
    }
    private void control(MarketOrder o,String action){
        var c=lifecycle.coordination(operator,o.orderId());
        lifecycle.control(operator,o.orderId(),new OrderControl(key(),Long.parseLong((String)c.get("version")),action,"joint fault "+action));
    }
    private void multiWorker() throws Exception {
        var o=create();var work=new ArrayList<Callable<TradeLease>>();
        for(int i=0;i<16;i++)work.add(()->tasks.claim(o.orderId(),30000));
        var claims=race(work);check(claims.stream().filter(Objects::nonNull).count()==1,"16 workers have one live lease");
        var d=tasks.beforeSend(claims.stream().filter(Objects::nonNull).findFirst().orElseThrow());var proof=remote.execute(d);
        var results=new ArrayList<Callable<Boolean>>();for(int i=0;i<8;i++)results.add(()->tasks.complete(d,proof));
        check(race(results).stream().filter(Boolean.TRUE::equals).count()==1,"8 duplicate reserve writebacks advance once");
        check(fixtures.count("SELECT COUNT(*) FROM b_trade_attempt WHERE order_id=?",o.orderId())==1,"one outbound attempt for one winning lease");
        lifecycle.cancel(user,o.orderId(),key(),"joint complete race");settle(o);
        checks.add("16 workers / one lease and outbound attempt / 8 result writebacks advance once");
    }
    private void cancelAndSend() throws Exception {
        for(int i=0;i<6;i++){
            var o=create();var lease=tasks.claim(o.orderId(),30000);String operation=key();
            var answers=race(List.<Callable<Object>>of(()->tasks.beforeSend(lease),()->lifecycle.cancel(user,o.orderId(),operation,"joint cancel/send")));
            var d=(TradeDispatch)answers.get(0);settle(o);
            if(d==null)check(fixtures.get(o).closeBasis().equals("LOCAL_NEVER_DISPATCHED"),"cancel winner proves strictly unsent");
            else{check(remote.execute(d).code().equals("ORDER_CLOSED"),"delayed reserve loses to close marker");check(!tasks.complete(d,new TradeReply("0000",TradeCommands.evidence(d.order()))),"late result cannot resurrect");}
        }
        var o=create();var writes=new ArrayList<Callable<Object>>();String stable=key();
        for(int i=0;i<8;i++)writes.add(()->lifecycle.cancel(user,o.orderId(),stable,"same original concurrent cancel"));
        var accepted=race(writes);check(accepted.stream().filter(x->!((OrderActionResult)x).replay()).count()==1,"same original cancel accepted once");settle(o);
        check(fixtures.count("SELECT COUNT(*) FROM b_order_operation WHERE order_id=?",o.orderId())==1,"same cancel one durable audit");
        checks.add("6 actual cancel/send races / close marker fences delayed sends / 8 concurrent original cancels one audit and release");
    }
    private void cancelAndResult() throws Exception {
        var o=create();var d=tasks.beforeSend(tasks.claim(o.orderId(),30000));var proof=remote.execute(d);
        race(List.<Callable<Object>>of(()->tasks.complete(d,proof),()->lifecycle.cancel(user,o.orderId(),key(),"cancel vs reserve writeback")));
        check(fixtures.get(o).businessStatus().equals("CLOSING"),"reserve success cannot override concurrent close");settle(o);
        checks.add("cancel versus successful reserve writeback / CLOSED final state / one release");
    }
    private void adjustmentAndReserve() throws Exception {
        for(int i=0;i<6;i++){
            var original=create();String sku=original.confirmation().conditions().goodsId();
            var c=orders.confirm(other,original.confirmation().conditions(),key());long version=inventory.detail(sku).version();
            var result=race(List.<Callable<Object>>of(
                ()->inventory.execute(operator,key(),new InventoryRequest("ADJUST",sku,-2,version,"compete with reserve")),
                ()->{try{return orders.create(other,key(),c.confirmationId(),key()).order();}catch(cn.zj.zjmarket.types.exception.InventoryFailure rejected){check(rejected.code().equals("STOCK_INSUFFICIENT"),"only insufficient stock can reject contender");return rejected.code();}}));
            var adjustment=(cn.zj.zjmarket.domain.inventory.model.valobj.InventoryWrite)result.get(0);
            boolean adjusted=adjustment.result().outcome().equals("SUCCEEDED");
            check(adjusted!=(result.get(1) instanceof MarketOrder),"exactly adjustment or competing reserve succeeds");
            var account=inventory.detail(sku);check(account.available()>=0&&account.reserved()==(adjusted?1:2),"adjustment never invades held stock");
            if(result.get(1) instanceof MarketOrder extra){lifecycle.cancel(other,extra.orderId(),key(),"release extra owned fixture");}
            lifecycle.cancel(user,original.orderId(),key(),"release original fixture");settle(original);
        }
        checks.add("6 adjustment versus reserve races / current version arbitrates / held stock cannot be adjusted away");
    }
    private void pauseInflight() throws Exception {
        var o=create();var d=tasks.beforeSend(tasks.claim(o.orderId(),800));var proof=remote.execute(d);
        control(o,"PAUSE");check(!tasks.complete(d,proof),"paused in-flight response cannot advance");
        control(o,"RESUME");check(tasks.claim(o.orderId(),30000)==null,"resume respects old request lease bound");
        Thread.sleep(900);fixtures.due(o);var fresh=tasks.beforeSend(tasks.claim(o.orderId(),30000));
        check(fresh.method().equals("query"),"resuming possibly dispatched order only queries original");tasks.complete(fresh,remote.execute(fresh));
        check(fixtures.get(o).businessStatus().equals("WAITING_PAYMENT"),"original query recovers remote success");
        check(fixtures.count("SELECT COUNT(*) FROM b_trade_attempt WHERE order_id=? AND method='reserve'",o.orderId())==1,"no extra reserve on resume");
        lifecycle.cancel(user,o.orderId(),key(),"cleanup paused fixture");settle(o);
        checks.add("PAUSE fences in-flight writer / RESUME waits existing lease / original QUERY recovers without duplicate reserve");
    }
    private void authStale() throws Exception {
        var o=create();var d=tasks.beforeSend(tasks.claim(o.orderId(),30000));var valid=CloseCommands.change(remote.execute(d).evidence(),"recordVersion","2");
        tasks.complete(d,new TradeReply("0000",valid));
        fixtures.sql("UPDATE b_trade_coordination SET intent='QUERY',intent_version=intent_version+1,run_state='READY',next_attempt_ms=0 WHERE order_id=?",o.orderId());
        var auth=tasks.beforeSend(tasks.claim(o.orderId(),30000));tasks.complete(auth,new TradeReply("INTEGRATION_AUTH_FAILED",null));control(o,"CHECK");
        var probe=tasks.beforeSend(tasks.claim(o.orderId(),30000));check(probe.method().equals("query"),"auth CHECK read only");
        tasks.complete(probe,new TradeReply("0000",CloseCommands.change(valid,"recordVersion","1")));fixtures.due(o);
        check(fixtures.get(o).reviewRequired()&&tasks.claim(o.orderId(),30000)==null,"stale authenticated reply cannot resume original task");
        check(fixtures.count("SELECT COUNT(*) FROM b_inventory_reservation WHERE order_id=? AND state='HELD'",o.orderId())==1,"stale auth check preserves reservation");
        checks.add("D33 authenticated but stale QUERY remains stopped and HELD / no automatic write replay");
    }
    private void conservation() throws Exception {
        String sql="SELECT a.available,a.reserved,a.sold,COALESCE((SELECT SUM(l.delta_available) FROM b_inventory_ledger l WHERE l.goods_id=a.goods_id),0),COALESCE((SELECT SUM(r.quantity) FROM b_inventory_reservation r WHERE r.goods_id=a.goods_id AND r.state='HELD'),0),COALESCE((SELECT SUM(l.delta_available) FROM b_inventory_ledger l WHERE l.goods_id=a.goods_id AND l.kind IN ('INBOUND','ADJUST')),0),(SELECT COUNT(*) FROM b_market_order o JOIN b_inventory_reservation r ON r.order_id=o.order_id JOIN b_trade_coordination t ON t.order_id=o.order_id WHERE o.goods_id=a.goods_id AND ((o.business_status='CLOSED' AND (r.state<>'RELEASED' OR t.run_state<>'DONE' OR EXISTS(SELECT 1 FROM b_purchase_guard g WHERE g.active_order_id=o.order_id))) OR (o.business_status<>'CLOSED' AND r.state<>'HELD'))) FROM b_inventory_account a WHERE a.goods_id=?";
        for(String sku:goods)try(var c=db.getConnection();var p=c.prepareStatement(sql)){
            p.setString(1,sku);try(var r=p.executeQuery()){check(r.next(),"owned account exists");long available=r.getLong(1),reserved=r.getLong(2),sold=r.getLong(3);
                check(available>=0&&reserved>=0&&sold==0,"nonnegative balances and no sold before payment");
                check(available==r.getLong(4)&&reserved==r.getLong(5)&&Math.addExact(available,reserved)==r.getLong(6),"ledger/reservation/physical inventory conservation");
                check(r.getLong(7)==0,"closed and held order/task/guard facts agree");
            }
        }
        checks.add("all "+goods.size()+" owned SKUs: available=ledger deltas / reserved=HELD quantity / available+reserved+sold=inbound+adjustment / order-task-guard agreement");
    }
    public static int run(){
        try{
            if(!env("B_DATABASE_SCOPE").equals("b02-test")||!env("B_DATABASE_USERNAME").equals("zj_market_b02_test_app")||!env("B_DATABASE_URL").matches("^jdbc:mysql://[^/]+/zj_market_b02_test(?:\\?.*)?$"))throw new IllegalArgumentException("Isolated B test database required");
            var app=new SpringApplication(CloseCommands.ProbeConfiguration.class,OrderCommands.ProbeConfiguration.class,ZjMarketApplication.class);
            try(var ctx=app.run("--server.port=0","--b.identity.enabled=true","--b.product.enabled=true","--b.inventory.enabled=true","--b.order.enabled=true","--b.trade.enabled=true","--b.trade.scheduler-enabled=false","--b.trial.enabled=false","--b.sync.enabled=false","--b.infrastructure.database.enabled=true","--b.infrastructure.rpc.enabled=false","--b.infrastructure.mq.enabled=false")){
                var identity=ctx.getBean(IIdentityService.class);String suffix=key().replace("-","").substring(0,12),password="Joint-"+key();
                var user=identity.register("jointu"+suffix,password,"joint user");var other=identity.register("jointv"+suffix,password,"joint other");var op=identity.initializeOperator("jointop"+suffix,password,"joint operator");
                var test=new JointFaultCommands(ctx,user.userId(),other.userId(),op.userId());
                test.multiWorker();test.cancelAndSend();test.cancelAndResult();test.adjustmentAndReserve();test.pauseInflight();test.authStale();test.conservation();
                var report=Path.of(env("B_JOINT_REPORT"));Files.createDirectories(report.toAbsolutePath().getParent());
                var json=new com.fasterxml.jackson.databind.ObjectMapper();Files.writeString(report,json.writeValueAsString(Map.of("status","PASSED","java",Runtime.version().toString(),"checks",test.checks,"ownedGoods",test.goods,"database","actual MySQL V9","port","verification-only controlled remote fault port; actual A separately tested","funds","NEVER_OPENED; no payment or refunds")));
                System.out.println("B03 combined faults and inventory conservation: PASSED");
            }return 0;
        }catch(Exception failure){System.err.println("B03 joint faults failed: "+failure.getClass().getSimpleName()+" "+(failure.getMessage()!=null&&failure.getMessage().startsWith("check:")?failure.getMessage():"details withheld"));try{Files.createDirectories(Path.of("target/joint-faults"));try(var w=new java.io.PrintWriter(Files.newBufferedWriter(Path.of("target/joint-faults/failure.txt")))){failure.printStackTrace(w);}}catch(Exception ignored){}return 1;}
    }
}
