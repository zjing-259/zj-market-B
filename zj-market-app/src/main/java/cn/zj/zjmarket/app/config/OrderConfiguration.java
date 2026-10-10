package cn.zj.zjmarket.app.config;
import cn.zj.zjmarket.domain.order.adapter.port.IPurchaseQuotePort;
import cn.zj.zjmarket.domain.order.adapter.repository.IOrderRepository;
import cn.zj.zjmarket.domain.order.service.IOrderService;
import cn.zj.zjmarket.domain.order.service.impl.OrderService;
import cn.zj.zjmarket.domain.product.service.IMarketingTrialService;
import cn.zj.zjmarket.infrastructure.adapter.port.order.DubboPurchaseQuote;
import cn.zj.zjmarket.infrastructure.adapter.repository.OrderRepository;
import cn.zj.zjmarket.infrastructure.config.properties.RpcSettings;
import cn.zj.zjmarket.infrastructure.gateway.rpc.RpcClientFactory;
import cn.zj.zjmarket.infrastructure.dao.*;
import javax.sql.DataSource;
import org.mybatis.spring.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.*;
import org.springframework.context.annotation.*;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
@Configuration(proxyBeanMethods=false)
@ConditionalOnProperty(name="b.order.enabled",havingValue="true")
public class OrderConfiguration {
 @Bean IOrderRepository orderRepository(DataSource db,@Value("${b.inventory.enabled:false}")boolean inventory,@Value("${b.identity.enabled:false}")boolean identity)throws Exception{
  if(!inventory||!identity)throw new IllegalArgumentException("Orders require inventory and identity");
  var factory=new SqlSessionFactoryBean();factory.setDataSource(db);var c=new org.apache.ibatis.session.Configuration();c.setLocalCacheScope(org.apache.ibatis.session.LocalCacheScope.STATEMENT);c.addMapper(IOrderDao.class);c.addMapper(IProductDao.class);c.addMapper(IInventoryDao.class);factory.setConfiguration(c);
  var sessions=new SqlSessionTemplate(factory.getObject());var tx=new TransactionTemplate(new DataSourceTransactionManager(db));tx.setIsolationLevel(org.springframework.transaction.TransactionDefinition.ISOLATION_READ_COMMITTED);tx.setTimeout(15);
  return new OrderRepository(sessions.getMapper(IOrderDao.class),sessions.getMapper(IProductDao.class),sessions.getMapper(IInventoryDao.class),tx);
 }
 @Bean(destroyMethod="close") @ConditionalOnMissingBean(IPurchaseQuotePort.class) DubboPurchaseQuote purchaseQuote(IMarketingTrialService trial,RpcSettings rpc,RpcClientFactory factory){return new DubboPurchaseQuote(trial,rpc,factory);}
 @Bean IOrderService orderService(IOrderRepository repo,IPurchaseQuotePort quote,@Value("${b.product.event-source:}")String source,@Value("${b.product.event-channel:}")String channel,@Value("${b.order.reserve-wait-millis:300000}")long reserveWaitMillis){return new OrderService(repo,quote,source,channel,reserveWaitMillis);}
}
