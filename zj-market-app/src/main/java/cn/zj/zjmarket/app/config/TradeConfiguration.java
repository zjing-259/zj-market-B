package cn.zj.zjmarket.app.config;
import cn.zj.zjmarket.domain.order.adapter.port.ITradePort;
import cn.zj.zjmarket.domain.order.adapter.repository.*;
import cn.zj.zjmarket.domain.order.service.*;
import cn.zj.zjmarket.domain.order.service.impl.TradeCoordinationService;
import cn.zj.zjmarket.infrastructure.adapter.port.order.DubboTradePort;
import cn.zj.zjmarket.infrastructure.adapter.repository.TradeRepository;
import cn.zj.zjmarket.infrastructure.config.properties.RpcSettings;
import cn.zj.zjmarket.infrastructure.gateway.rpc.RpcClientFactory;
import cn.zj.zjmarket.infrastructure.dao.*;
import cn.zj.zjmarket.trigger.job.TradeRecoveryJob;
import javax.sql.DataSource;
import org.mybatis.spring.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.*;
import org.springframework.context.annotation.*;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
@Configuration(proxyBeanMethods=false) @ConditionalOnProperty(name="b.trade.enabled",havingValue="true")
public class TradeConfiguration {
 @Bean TradeRepository tradeRepository(DataSource db,IOrderRepository orders,@Value("${b.trade.retry-base-millis:2000}")long retryBase,@Value("${b.trade.retry-max-millis:30000}")long retryMax)throws Exception{var f=new SqlSessionFactoryBean();f.setDataSource(db);var c=new org.apache.ibatis.session.Configuration();c.setLocalCacheScope(org.apache.ibatis.session.LocalCacheScope.STATEMENT);for(var type:java.util.List.of(ITradeDao.class,IOrderDao.class,IProductDao.class,IInventoryDao.class))c.addMapper(type);f.setConfiguration(c);var sessions=new SqlSessionTemplate(f.getObject());var tx=new TransactionTemplate(new DataSourceTransactionManager(db));tx.setIsolationLevel(org.springframework.transaction.TransactionDefinition.ISOLATION_READ_COMMITTED);tx.setTimeout(15);return new TradeRepository(sessions.getMapper(ITradeDao.class),sessions.getMapper(IOrderDao.class),sessions.getMapper(IProductDao.class),sessions.getMapper(IInventoryDao.class),orders,tx,retryBase,retryMax);}
 @Bean(destroyMethod="close") @ConditionalOnMissingBean(ITradePort.class) DubboTradePort tradePort(RpcSettings rpc,RpcClientFactory factory,@Value("${b.product.event-source:}")String source,@Value("${b.product.event-channel:}")String channel){if(!source.equals(rpc.getSource())||!channel.equals(rpc.getChannel()))throw new IllegalArgumentException("Trade and RPC scopes must agree");return new DubboTradePort(rpc,factory);}
 @Bean ITradeCoordinationService tradeService(ITradeRepository repo,ITradePort port,@Value("${b.trade.lease-millis:30000}")long lease){if(lease<15000||lease>300000)throw new IllegalArgumentException("Invalid trade lease");return new TradeCoordinationService(repo,port,lease);}
 @Bean IOrderLifecycleService orderLifecycleService(IOrderLifecycleRepository repo){return new cn.zj.zjmarket.domain.order.service.impl.OrderLifecycleService(repo);}
 @Bean ITeamService teamService(ITradePort port,IOrderRepository orders){return new cn.zj.zjmarket.domain.order.service.impl.TeamService(port,orders);}
 @Bean TradeRecoveryJob tradeRecoveryJob(ITradeCoordinationService service,@Value("${b.trade.scan-millis:2000}")long scan,@Value("${b.trade.batch-size:20}")int batch,@Value("${b.trade.scheduler-enabled:true}")boolean enabled){if(scan<100||scan>60000||batch<1||batch>100)throw new IllegalArgumentException("Invalid trade scan");return new TradeRecoveryJob(service,scan,batch,enabled);}
}
