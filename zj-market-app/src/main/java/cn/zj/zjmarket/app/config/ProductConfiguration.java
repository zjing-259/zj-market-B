package cn.zj.zjmarket.app.config;

import cn.zj.zjmarket.domain.product.adapter.port.IProductEventPort;
import cn.zj.zjmarket.domain.product.adapter.repository.IProductRepository;
import cn.zj.zjmarket.domain.product.service.IProductService;
import cn.zj.zjmarket.domain.product.service.impl.ProductService;
import cn.zj.zjmarket.infrastructure.adapter.port.product.ContractProductEvents;
import cn.zj.zjmarket.infrastructure.adapter.repository.ProductRepository;
import cn.zj.zjmarket.infrastructure.dao.IProductDao;
import java.time.Clock;
import javax.sql.DataSource;
import org.mybatis.spring.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.*;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
@Configuration(proxyBeanMethods=false)
@ConditionalOnProperty(name="b.product.enabled",havingValue="true")
public class ProductConfiguration {
    @Bean IProductRepository productStore(DataSource db,@Value("${b.identity.enabled:false}")boolean identity)throws Exception {
        if(!identity)throw new IllegalArgumentException("Product HTTP requires identity to be enabled");
        var factory=new SqlSessionFactoryBean();factory.setDataSource(db);var config=new org.apache.ibatis.session.Configuration();config.addMapper(IProductDao.class);
        config.setLocalCacheScope(org.apache.ibatis.session.LocalCacheScope.STATEMENT);factory.setConfiguration(config);
        var tx=new TransactionTemplate(new DataSourceTransactionManager(db));
        // Consistent list/details/product+progress across concurrent edits. Writes lock then compare expected version.
        tx.setIsolationLevel(org.springframework.transaction.TransactionDefinition.ISOLATION_REPEATABLE_READ);tx.setTimeout(15);
        return new ProductRepository(new SqlSessionTemplate(factory.getObject()).getMapper(IProductDao.class),tx);
    }
    @Bean IProductEventPort productEvents(@Value("${b.product.event-producer:}")String producer,@Value("${b.product.event-source:}")String source,@Value("${b.product.event-channel:}")String channel){return new ContractProductEvents(producer,source,channel);}
    @Bean IProductService productService(IProductRepository store,IProductEventPort events){return new ProductService(store,events,Clock.systemUTC());}
}
