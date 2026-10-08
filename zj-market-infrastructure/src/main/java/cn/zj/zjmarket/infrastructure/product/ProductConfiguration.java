package cn.zj.zjmarket.infrastructure.product;
import cn.zj.zjmarket.application.product.*;
import org.springframework.context.annotation.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import org.mybatis.spring.*;
import javax.sql.DataSource;
import java.time.Clock;
@Configuration(proxyBeanMethods=false)
@ConditionalOnProperty(name="b.product.enabled",havingValue="true")
public class ProductConfiguration {
    @Bean ProductStore productStore(DataSource db,@Value("${b.identity.enabled:false}")boolean identity)throws Exception {
        if(!identity)throw new IllegalArgumentException("Product HTTP requires identity to be enabled");
        var factory=new SqlSessionFactoryBean();factory.setDataSource(db);var config=new org.apache.ibatis.session.Configuration();config.addMapper(ProductMapper.class);
        config.setLocalCacheScope(org.apache.ibatis.session.LocalCacheScope.STATEMENT);factory.setConfiguration(config);
        var tx=new TransactionTemplate(new DataSourceTransactionManager(db));
        // Consistent list/details/product+progress across concurrent edits. Writes lock then compare expected version.
        tx.setIsolationLevel(org.springframework.transaction.TransactionDefinition.ISOLATION_REPEATABLE_READ);tx.setTimeout(15);
        return new MyBatisProductStore(new SqlSessionTemplate(factory.getObject()).getMapper(ProductMapper.class),tx);
    }
    @Bean ProductEventPort productEvents(@Value("${b.product.event-producer:}")String producer,@Value("${b.product.event-source:}")String source,@Value("${b.product.event-channel:}")String channel){return new ContractProductEvents(producer,source,channel);}
    @Bean ProductService productService(ProductStore store,ProductEventPort events){return new ProductService(store,events,Clock.systemUTC());}
}
