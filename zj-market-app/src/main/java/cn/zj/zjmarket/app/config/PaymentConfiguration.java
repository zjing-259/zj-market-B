package cn.zj.zjmarket.app.config;
import cn.zj.zjmarket.domain.payment.adapter.repository.*;
import cn.zj.zjmarket.domain.payment.adapter.port.*;
import cn.zj.zjmarket.domain.payment.service.IPaymentService;
import cn.zj.zjmarket.domain.payment.service.impl.PaymentService;
import cn.zj.zjmarket.domain.order.adapter.port.ITradePort;
import cn.zj.zjmarket.domain.order.adapter.repository.IOrderRepository;
import cn.zj.zjmarket.infrastructure.adapter.repository.PaymentRepository;
import cn.zj.zjmarket.infrastructure.adapter.port.payment.SimulatedChannel;
import cn.zj.zjmarket.trigger.job.PaymentRecoveryJob;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.*;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import javax.sql.DataSource;
@Configuration(proxyBeanMethods=false)
@ConditionalOnProperty(name="b.payment.enabled",havingValue="true")
public class PaymentConfiguration {
 private static TransactionTemplate transaction(DataSource source){var tx=new TransactionTemplate(new DataSourceTransactionManager(source));tx.setIsolationLevel(org.springframework.transaction.TransactionDefinition.ISOLATION_READ_COMMITTED);tx.setTimeout(15);return tx;}
 @Bean IPaymentRepository paymentRepository(DataSource db,IOrderRepository orders){return new PaymentRepository(db,transaction(db),orders);}
 @Bean ISimulatedChannel simulatedChannel(DataSource db){return new SimulatedChannel(db,transaction(db));}
 @Bean IPaymentService paymentService(IPaymentRepository repo,ISimulatedChannel channel,ITradePort trade,@Value("${b.payment.checkout-enabled:false}")boolean enabled,@Value("${b.payment.max-query-rtt-millis:2000}")long rtt,@Value("${b.payment.time-evidence-ttl-millis:2000}")long ttl,@Value("${b.payment.max-clock-skew-millis:2000}")long skew){return new PaymentService(repo,channel,trade,enabled,rtt,ttl,skew);}
 @Bean PaymentRecoveryJob paymentRecoveryJob(IPaymentService service,@Value("${b.payment.scheduler-enabled:true}")boolean enabled){return new PaymentRecoveryJob(service,enabled);}
}
