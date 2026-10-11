package cn.zj.zjmarket.app.config;
import cn.zj.zjmarket.domain.order.adapter.repository.IOrderRepository;
import cn.zj.zjmarket.domain.order.service.ITradeCoordinationService;
import cn.zj.zjmarket.domain.payment.adapter.port.*;
import cn.zj.zjmarket.domain.payment.adapter.repository.ISettlementRepository;
import cn.zj.zjmarket.domain.reconciliation.adapter.port.IReconciliationPort;
import cn.zj.zjmarket.domain.reconciliation.service.ReconciliationService;
import cn.zj.zjmarket.infrastructure.adapter.repository.*;
import cn.zj.zjmarket.infrastructure.adapter.port.reconciliation.DubboReconciliationPort;
import cn.zj.zjmarket.infrastructure.gateway.rpc.RpcClientFactory;
import cn.zj.zjmarket.infrastructure.config.properties.RpcSettings;
import cn.zj.zjmarket.trigger.job.ReconciliationJob;
import org.springframework.context.annotation.*;
import org.springframework.boot.autoconfigure.condition.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import javax.sql.DataSource;
@Configuration(proxyBeanMethods=false)
@ConditionalOnProperty(name="b.trade.events-enabled",havingValue="true")
@ConditionalOnExpression("${b.reconciliation.enabled:false} or ${b.reconciliation.recovery-enabled:true}")
public class ReconciliationConfiguration {
 @Bean @DependsOn("paymentClosing") ReconciliationRepository reconciliationRepository(DataSource ds,IOrderRepository orders,TradeRepository trades,ITradeCoordinationService closer,ISettlementRepository settlement,RpcSettings rpc){var tx=new TransactionTemplate(new DataSourceTransactionManager(ds));tx.setIsolationLevel(org.springframework.transaction.TransactionDefinition.ISOLATION_READ_COMMITTED);tx.setTimeout(15);var repo=new ReconciliationRepository(ds,tx,orders,trades,closer,rpc.getSource(),rpc.getChannel());repo.validateSchema();var blocks=new OrderReviewBlocks(new org.springframework.jdbc.core.JdbcTemplate(ds));trades.enableReconciliation(blocks::canRecover);((SettlementRepository)settlement).enableReconciliation(blocks);return repo;}
 @Bean(destroyMethod="close") @ConditionalOnMissingBean(IReconciliationPort.class) DubboReconciliationPort reconciliationPort(RpcSettings rpc,RpcClientFactory factory){if(!rpc.isEnabled())throw new IllegalArgumentException("Reconciliation requires authenticated RPC");return new DubboReconciliationPort(rpc,factory);}
 @Bean ReconciliationService reconciliationService(ReconciliationRepository repo,IReconciliationPort port,ISimulatedChannel simulator,ISettlementRepository settlement){return new ReconciliationService(repo,port,(IChannelFacts)simulator,settlement);}
 @Bean ReconciliationJob reconciliationJob(ReconciliationService service,@Value("${b.reconciliation.scheduler-enabled:true}")boolean scheduler,@Value("${b.reconciliation.enabled:false}")boolean discover){return new ReconciliationJob(service,scheduler,discover);}
}
