package cn.zj.zjmarket.app.config;
import cn.zj.zjmarket.domain.refund.model.Refund.Settings;
import cn.zj.zjmarket.domain.refund.service.RefundService;
import cn.zj.zjmarket.infrastructure.adapter.repository.RefundRepository;
import cn.zj.zjmarket.infrastructure.adapter.port.refund.SimulatedRefundChannel;
import cn.zj.zjmarket.infrastructure.config.properties.RpcSettings;
import cn.zj.zjmarket.trigger.job.RefundRecoveryJob;
import org.springframework.context.annotation.*;
import org.springframework.boot.autoconfigure.condition.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import javax.sql.DataSource;
@Configuration(proxyBeanMethods=false)
@ConditionalOnProperty(name="b.trade.events-enabled",havingValue="true")
@ConditionalOnExpression("${b.refund.enabled:false} or ${b.refund.recovery-enabled:true}")
public class RefundConfiguration {
 @Bean org.springframework.beans.factory.InitializingBean refundSync(DataSource ds,RefundRepository repo,cn.zj.zjmarket.domain.payment.adapter.repository.ISettlementRepository settlement,cn.zj.zjmarket.domain.order.adapter.repository.IOrderRepository orders,cn.zj.zjmarket.infrastructure.config.properties.MqSettings mq){return ()->{var db=new org.springframework.jdbc.core.JdbcTemplate(ds);repo.enableOutbox(new cn.zj.zjmarket.infrastructure.adapter.repository.RefundOutbox(db,mq.getProducerId(),mq.getSource(),mq.getChannel()));((cn.zj.zjmarket.infrastructure.adapter.repository.SettlementRepository)settlement).enableRefundSync(repo,new cn.zj.zjmarket.infrastructure.adapter.repository.RefundSyncRepository(db,repo,orders));};}
 @Bean cn.zj.zjmarket.infrastructure.adapter.repository.RefundReleaseRepository refundReleaseRepository(DataSource ds,RefundRepository refunds){var repo=new cn.zj.zjmarket.infrastructure.adapter.repository.RefundReleaseRepository(ds,refunds);repo.validateSchema();return repo;}
 @Bean cn.zj.zjmarket.trigger.job.RefundReleaseJob refundReleaseJob(cn.zj.zjmarket.infrastructure.adapter.repository.RefundReleaseRepository repo,@Value("${b.refund.scheduler-enabled:true}")boolean enabled){return new cn.zj.zjmarket.trigger.job.RefundReleaseJob(()->repo.tick(20),enabled);}
 @Bean Settings refundSettings(@Value("${b.refund.scan-millis:2000}")long scan,@Value("${b.refund.timeout-millis:10000}")long timeout,@Value("${b.refund.lease-millis:30000}")long lease,@Value("${b.refund.renew-millis:20000}")long renew,@Value("${b.refund.retry-base-millis:2000}")long base,@Value("${b.refund.retry-cap-millis:30000}")long cap,@Value("${b.refund.jitter-millis:250}")long jitter){return new Settings(scan,timeout,lease,renew,base,cap,jitter);}
 private TransactionTemplate transaction(DataSource ds){var tx=new TransactionTemplate(new DataSourceTransactionManager(ds));tx.setIsolationLevel(org.springframework.transaction.TransactionDefinition.ISOLATION_READ_COMMITTED);tx.setTimeout(15);return tx;}
 @Bean RefundRepository refundRepository(DataSource ds,Settings settings,RpcSettings rpc){var repo=new RefundRepository(ds,transaction(ds),settings,rpc.getSource(),rpc.getChannel());repo.validateSchema();return repo;}
 @Bean SimulatedRefundChannel simulatedRefundChannel(DataSource ds,Settings settings){return new SimulatedRefundChannel(ds,transaction(ds),settings);}
 @Bean(destroyMethod="close") RefundService refundService(RefundRepository repo,SimulatedRefundChannel channel,Settings settings){return new RefundService(repo,channel,settings);}
 @Bean RefundRecoveryJob refundRecoveryJob(RefundService service,Settings settings,@Value("${b.refund.scheduler-enabled:true}")boolean scheduler,@Value("${b.refund.enabled:false}")boolean discover){return new RefundRecoveryJob(service,settings,scheduler,discover);}
}
