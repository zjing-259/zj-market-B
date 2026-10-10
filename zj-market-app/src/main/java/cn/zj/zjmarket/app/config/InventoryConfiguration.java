package cn.zj.zjmarket.app.config;
import cn.zj.zjmarket.domain.inventory.adapter.repository.IInventoryRepository;
import cn.zj.zjmarket.domain.inventory.service.IInventoryService;
import cn.zj.zjmarket.domain.inventory.service.impl.InventoryService;
import cn.zj.zjmarket.infrastructure.adapter.repository.InventoryRepository;
import cn.zj.zjmarket.infrastructure.dao.IInventoryDao;
import javax.sql.DataSource;
import org.mybatis.spring.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.*;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
@Configuration(proxyBeanMethods=false)
@ConditionalOnProperty(name="b.inventory.enabled",havingValue="true")
public class InventoryConfiguration {
 @Bean IInventoryRepository inventoryRepository(DataSource db,@Value("${b.identity.enabled:false}")boolean identity,@Value("${b.product.enabled:false}")boolean product)throws Exception{
  if(!identity||!product)throw new IllegalArgumentException("Inventory requires identity and products");
  var f=new SqlSessionFactoryBean();f.setDataSource(db);var c=new org.apache.ibatis.session.Configuration();c.addMapper(IInventoryDao.class);c.setLocalCacheScope(org.apache.ibatis.session.LocalCacheScope.STATEMENT);f.setConfiguration(c);
  var tx=new TransactionTemplate(new DataSourceTransactionManager(db));tx.setIsolationLevel(org.springframework.transaction.TransactionDefinition.ISOLATION_READ_COMMITTED);tx.setTimeout(15);
  return new InventoryRepository(new SqlSessionTemplate(f.getObject()).getMapper(IInventoryDao.class),tx);
 }
 @Bean IInventoryService inventoryService(IInventoryRepository repository){return new InventoryService(repository);}
}
