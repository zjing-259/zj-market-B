package cn.zj.zjmarket.test.config;

import cn.zj.zjmarket.app.config.InfrastructureConfiguration;
import cn.zj.zjmarket.infrastructure.config.properties.MqSettings;
import cn.zj.zjmarket.infrastructure.gateway.mq.MqClientFactory;
import cn.zj.zjmarket.infrastructure.gateway.rpc.RpcClientFactory;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.*;
class ConfigurationBoundaryTests {
    private final ApplicationContextRunner runner = new ApplicationContextRunner()
            .withUserConfiguration(InfrastructureConfiguration.class);

    @Test void disabledAdaptersNeedNoCredentialsAndIgnoreInheritedADatasource() {
        runner.withPropertyValues("spring.datasource.url=jdbc:mysql://127.0.0.1/group_buy_market_phase1_test",
                "spring.datasource.username=unused-a-user").run(context -> {
            assertThat(context).hasNotFailed();
            assertThat(context).doesNotHaveBean(DataSource.class)
                    .doesNotHaveBean(RpcClientFactory.class).doesNotHaveBean(MqClientFactory.class);
        });
    }

    @Test void rpcEnablementRequiresAnExternalSecret() {
        runner.withPropertyValues(
                "b.infrastructure.rpc.enabled=true",
                "b.infrastructure.rpc.url=tri://127.0.0.1:50051?ssl-enabled=true",
                "b.infrastructure.rpc.group=gbm-dev",
                "b.infrastructure.rpc.client-id=public-test-client",
                "b.infrastructure.rpc.key-id=public-test-key").run(context -> {
            assertThat(context).hasFailed();
            assertThat(context.getStartupFailure()).hasRootCauseMessage("Missing external configuration: rpc.secret");
        });
    }

    @Test void bCannotUseTheADatabaseEvenWhenExplicitlyEnabled() {
        runner.withPropertyValues("b.infrastructure.database.enabled=true",
                "b.infrastructure.database.url=jdbc:mysql://127.0.0.1/group_buy_market_phase1_test").run(context -> {
            assertThat(context).hasFailed();
            assertThat(context.getStartupFailure()).hasRootCauseMessage("B datasource must use a dedicated zj_market schema");
        });
    }

    @Test void bDatabaseCredentialsDoNotFallBackToACredentials() {
        runner.withPropertyValues("b.infrastructure.database.enabled=true",
                "b.infrastructure.database.url=jdbc:mysql://127.0.0.1/zj_market_test?serverTimezone=UTC",
                "b.infrastructure.database.username=public-test-user",
                "spring.datasource.password=public-test-a-password").run(context -> {
            assertThat(context).hasFailed();
            assertThat(context.getStartupFailure()).hasRootCauseMessage("Missing external configuration: database.password");
        });
    }

    @Test void mqPlaintextNeedsBothExplicitPermissionAndLoopbackAddress() {
        MqSettings settings = new MqSettings();
        settings.setNameserver("192.0.2.1:9876");
        settings.setAccessKey("public-test-key"); settings.setSecretKey("public-test-secret");
        settings.setProducerId("public-test-b"); settings.setBKeyId("public-b-key");
        settings.setBSecret("public-b-secret"); settings.setAKeyId("public-a-key");
        settings.setASecret("public-a-secret"); settings.setSource("s01"); settings.setChannel("c01");
        settings.setProductTopic("B_PRODUCT_EVENTS-dev"); settings.setResultTopic("A_INTEGRATION_RESULTS-dev");
        settings.setTeamTopic("A_TEAM_EVENTS-dev"); settings.setResultConsumerGroup("B_INTEGRATION_RESULTS-dev");
        settings.setUseTls(false); settings.setAllowPlaintextLoopback(true);
        assertThrows(IllegalStateException.class, settings::validate);
        settings.setNameserver("127.0.0.1:9876"); settings.setAllowPlaintextLoopback(false);
        assertThrows(IllegalStateException.class, settings::validate);
        settings.setAllowPlaintextLoopback(true);
        assertDoesNotThrow(settings::validate);
    }
}
