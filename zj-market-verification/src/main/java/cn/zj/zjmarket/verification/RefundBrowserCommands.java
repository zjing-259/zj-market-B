package cn.zj.zjmarket.verification;
import cn.zj.zjmarket.ZjMarketApplication;
import cn.zj.zjmarket.domain.refund.model.Refund.Settings;
import cn.zj.zjmarket.domain.refund.service.RefundService;
import cn.zj.zjmarket.infrastructure.adapter.repository.*;
import cn.zj.zjmarket.infrastructure.adapter.port.refund.SimulatedRefundChannel;
import org.springframework.boot.SpringApplication;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import javax.sql.DataSource;
import java.nio.file.*;
import static cn.zj.zjmarket.verification.ProductCommands.*;
final class RefundBrowserCommands {
 static int run(){try{check(env("B_DATABASE_SCOPE").equals("b02-test")&&env("B_DATABASE_USERNAME").equals("zj_market_b02_test_app"),"isolated browser scope");Path work=Path.of(env("B_PAYMENT_WORK"));var fixture=new com.fasterxml.jackson.databind.ObjectMapper().readTree(Files.readString(work.resolve("browser-private.json")));String refund=fixture.path("refundId").asText();check(refund.matches("[A-Za-z0-9_-]{1,64}"),"owned browser refund");
 try(var ctx=new SpringApplication(ReconciliationCommands.Config.class,OrderCommands.ProbeConfiguration.class,ZjMarketApplication.class).run("--server.port=18092","--b.identity.enabled=true","--b.product.enabled=true","--b.inventory.enabled=true","--b.order.enabled=true","--b.trade.enabled=true","--b.trade.scheduler-enabled=false","--b.payment.enabled=true","--b.payment.checkout-enabled=false","--b.payment.scheduler-enabled=false","--b.trade.events-enabled=false","--b.refund.scheduler-enabled=false","--b.trial.enabled=false","--b.sync.enabled=false","--b.infrastructure.database.enabled=true","--b.infrastructure.rpc.enabled=false","--b.infrastructure.mq.enabled=false")){
 var ds=ctx.getBean(DataSource.class);var db=new JdbcTemplate(ds);var transaction=new TransactionTemplate(new DataSourceTransactionManager(ds));transaction.setIsolationLevel(org.springframework.transaction.TransactionDefinition.ISOLATION_READ_COMMITTED);var repo=new RefundRepository(ds,transaction,Settings.defaults(),"s01","c01");repo.enableOutbox(new RefundOutbox(db,"zj-market","s01","c01"));ctx.getBean(RefundOperationsRepository.class).enableRecovery(repo);try(var service=new RefundService(repo,new SimulatedRefundChannel(ds,transaction,Settings.defaults()),Settings.defaults())){Files.writeString(work.resolve("browser-ready.txt"),"READY");long deadline=System.nanoTime()+java.util.concurrent.TimeUnit.MINUTES.toNanos(5);try{while(!Files.exists(work.resolve("browser-stop.txt"))){if(System.nanoTime()>deadline)throw new IllegalStateException("browser deadline");Thread.sleep(200);}}finally{service.recover(refund);}}}
 return 0;}catch(Exception e){System.err.println("Refund browser server failed: "+e.getClass().getSimpleName());return 1;}}
}
