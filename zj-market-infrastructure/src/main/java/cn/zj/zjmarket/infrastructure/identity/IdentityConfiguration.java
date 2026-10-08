package cn.zj.zjmarket.infrastructure.identity;
import cn.zj.zjmarket.application.identity.*;
import cn.zj.zjmarket.infrastructure.config.DatabaseSettings;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.*;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import org.mybatis.spring.SqlSessionFactoryBean;
import org.mybatis.spring.SqlSessionTemplate;
import org.springframework.security.crypto.argon2.Argon2PasswordEncoder;
import org.springframework.security.crypto.password.DelegatingPasswordEncoder;
import javax.sql.DataSource;
import java.time.Clock;
import java.util.Map;
@Configuration(proxyBeanMethods=false)
@EnableConfigurationProperties(IdentitySettings.class)
public class IdentityConfiguration {
    @Configuration(proxyBeanMethods=false)
    @ConditionalOnProperty(name="b.identity.enabled",havingValue="true")
    static class Enabled {
        @Bean IdentityStore identityStore(DataSource dataSource,DatabaseSettings db)throws Exception {
            if(!db.isEnabled()) throw new IllegalArgumentException("Identity requires explicit B database configuration");
            var factory=new SqlSessionFactoryBean();factory.setDataSource(dataSource);
            var config=new org.apache.ibatis.session.Configuration();config.addMapper(IdentityMapper.class);
            // Refresh row-lock rechecks must query the database, never a session cache.
            config.setLocalCacheScope(org.apache.ibatis.session.LocalCacheScope.STATEMENT);
            factory.setConfiguration(config);
            var mapper=new SqlSessionTemplate(factory.getObject()).getMapper(IdentityMapper.class);
            var tx=new TransactionTemplate(new DataSourceTransactionManager(dataSource));
            tx.setIsolationLevel(org.springframework.transaction.TransactionDefinition.ISOLATION_READ_COMMITTED);
            tx.setTimeout(15);
            return new MyBatisIdentityStore(mapper,tx);
        }
        @Bean PasswordPort passwordPort(){
            // User-selected Argon2id: 16-byte salt, 32-byte hash, 19 MiB, 2 iterations, 1 lane.
            var encoder=new DelegatingPasswordEncoder("argon2id",Map.of("argon2id",new Argon2PasswordEncoder(16,32,1,19456,2)));
            return new PasswordPort(){
                public String encode(String raw){return encoder.encode(raw);}
                public boolean matches(String raw,String hash){try{return encoder.matches(raw,hash);}catch(IllegalArgumentException e){throw new AuthFailure(503,"DEPENDENCY_UNAVAILABLE");}}
            };
        }
        @Bean AccessTokenPort accessTokenPort(IdentitySettings settings)throws Exception{return new RsaAccessTokens(settings,Clock.systemUTC());}
        @Bean IdentityService identityService(IdentityStore store,PasswordPort passwords,AccessTokenPort tokens,IdentitySettings settings){
            settings.validate();return new IdentityService(store,passwords,tokens,Clock.systemUTC(),settings.getAccessSeconds(),settings.getRefreshSeconds());
        }
    }
}
