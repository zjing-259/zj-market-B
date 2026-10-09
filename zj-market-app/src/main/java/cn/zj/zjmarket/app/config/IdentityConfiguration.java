package cn.zj.zjmarket.app.config;

import cn.zj.zjmarket.domain.identity.adapter.port.IAccessTokenPort;
import cn.zj.zjmarket.domain.identity.adapter.port.IPasswordPort;
import cn.zj.zjmarket.domain.identity.adapter.repository.IIdentityRepository;
import cn.zj.zjmarket.domain.identity.service.IIdentityService;
import cn.zj.zjmarket.domain.identity.service.impl.IdentityService;
import cn.zj.zjmarket.infrastructure.adapter.port.identity.Argon2Passwords;
import cn.zj.zjmarket.infrastructure.adapter.port.identity.RsaAccessTokens;
import cn.zj.zjmarket.infrastructure.adapter.repository.IdentityRepository;
import cn.zj.zjmarket.infrastructure.config.properties.DatabaseSettings;
import cn.zj.zjmarket.infrastructure.config.properties.IdentitySettings;
import cn.zj.zjmarket.infrastructure.dao.IIdentityDao;
import java.time.Clock;
import javax.sql.DataSource;
import org.mybatis.spring.SqlSessionFactoryBean;
import org.mybatis.spring.SqlSessionTemplate;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.*;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
@Configuration(proxyBeanMethods=false)
@EnableConfigurationProperties(IdentitySettings.class)
public class IdentityConfiguration {
    @Configuration(proxyBeanMethods=false)
    @ConditionalOnProperty(name="b.identity.enabled",havingValue="true")
    static class Enabled {
        @Bean IIdentityRepository identityStore(DataSource dataSource,DatabaseSettings db)throws Exception {
            if(!db.isEnabled()) throw new IllegalArgumentException("Identity requires explicit B database configuration");
            var factory=new SqlSessionFactoryBean();factory.setDataSource(dataSource);
            var config=new org.apache.ibatis.session.Configuration();config.addMapper(IIdentityDao.class);
            // Refresh row-lock rechecks must query the database, never a session cache.
            config.setLocalCacheScope(org.apache.ibatis.session.LocalCacheScope.STATEMENT);
            factory.setConfiguration(config);
            var mapper=new SqlSessionTemplate(factory.getObject()).getMapper(IIdentityDao.class);
            var tx=new TransactionTemplate(new DataSourceTransactionManager(dataSource));
            tx.setIsolationLevel(org.springframework.transaction.TransactionDefinition.ISOLATION_READ_COMMITTED);
            tx.setTimeout(15);
            return new IdentityRepository(mapper,tx);
        }
        @Bean IPasswordPort passwordPort(){return new Argon2Passwords();}
        @Bean IAccessTokenPort accessTokenPort(IdentitySettings settings)throws Exception{return new RsaAccessTokens(settings,Clock.systemUTC());}
        @Bean IIdentityService identityService(IIdentityRepository store,IPasswordPort passwords,IAccessTokenPort tokens,IdentitySettings settings){
            settings.validate();return new IdentityService(store,passwords,tokens,Clock.systemUTC(),settings.getAccessSeconds(),settings.getRefreshSeconds());
        }
    }
}
