package cn.zj.zjmarket.app.config;

import cn.zj.zjmarket.infrastructure.config.properties.DatabaseSettings;
import cn.zj.zjmarket.infrastructure.config.properties.MqSettings;
import cn.zj.zjmarket.infrastructure.config.properties.RpcSettings;
import cn.zj.zjmarket.infrastructure.gateway.codec.ContractCodec;
import cn.zj.zjmarket.infrastructure.gateway.mq.MqClientFactory;
import cn.zj.zjmarket.infrastructure.gateway.rpc.RpcClientFactory;
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties({RpcSettings.class, MqSettings.class, DatabaseSettings.class})
public class InfrastructureConfiguration {
    @Bean public ContractCodec contractCodec() { return new ContractCodec(); }

    @Bean
    @ConditionalOnProperty(name = "b.infrastructure.rpc.enabled", havingValue = "true")
    public RpcClientFactory rpcClientFactory(RpcSettings settings) {
        settings.validate();
        return new RpcClientFactory(settings);
    }

    @Bean
    @ConditionalOnProperty(name = "b.infrastructure.mq.enabled", havingValue = "true")
    public MqClientFactory mqClientFactory(MqSettings settings) {
        settings.validate();
        return new MqClientFactory(settings);
    }

    @Bean(destroyMethod = "close")
    @ConditionalOnProperty(name = "b.infrastructure.database.enabled", havingValue = "true")
    public HikariDataSource dataSource(DatabaseSettings settings) {
        settings.validate();
        HikariConfig config = new HikariConfig();
        config.setJdbcUrl(settings.getUrl());
        config.setUsername(settings.getUsername());
        config.setPassword(settings.getPassword());
        config.setDriverClassName("com.mysql.cj.jdbc.Driver");
        config.setPoolName("zj-market");
        config.setMaximumPoolSize(settings.getMaximumPoolSize());
        config.setMinimumIdle(0);
        config.setConnectionTimeout(settings.getConnectionTimeoutMillis());
        // Connection acquisition is explicit; merely wiring B must not run migrations or touch A.
        config.setInitializationFailTimeout(-1);
        return new HikariDataSource(config);
    }
}
