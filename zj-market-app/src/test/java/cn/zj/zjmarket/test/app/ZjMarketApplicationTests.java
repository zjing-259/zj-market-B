package cn.zj.zjmarket.test.app;

import cn.zj.zjmarket.infrastructure.config.properties.DatabaseSettings;
import cn.zj.zjmarket.infrastructure.config.properties.MqSettings;
import cn.zj.zjmarket.infrastructure.config.properties.RpcSettings;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.ApplicationContext;
import static org.junit.jupiter.api.Assertions.*;
@SpringBootTest(properties={"b.infrastructure.database.enabled=false","b.infrastructure.rpc.enabled=false","b.infrastructure.mq.enabled=false","b.identity.enabled=false","b.product.enabled=false","b.sync.enabled=false","b.trial.enabled=false"})
class ZjMarketApplicationTests {
    @Autowired ApplicationContext context;

    @Test void normalBootstrapDoesNotRunVerificationOrOpenExternalClients() {
        assertFalse(context.getBean(RpcSettings.class).isEnabled());
        assertFalse(context.getBean(MqSettings.class).isEnabled());
        assertFalse(context.getBean(DatabaseSettings.class).isEnabled());
        assertFalse(context.containsBean("rpcClientFactory"));
        assertFalse(context.containsBean("mqClientFactory"));
        assertTrue(context.getBeansOfType(DataSource.class).isEmpty());
        assertThrows(ClassNotFoundException.class, () -> Class.forName(
                "cn.zj.zjmarket.verification.EnvironmentProbe", false, getClass().getClassLoader()));
        assertNull(getClass().getResource("/application-environment-probe.properties"));
    }
    @Test void livenessRouteIsRegisteredByTheNormalBootstrap() {
        var mappings=context.getBean(org.springframework.web.servlet.mvc.method.annotation.RequestMappingHandlerMapping.class);
        assertTrue(mappings.getHandlerMethods().keySet().stream().anyMatch(mapping ->
                mapping.getPatternValues().contains("/internal/health/live") &&
                mapping.getMethodsCondition().getMethods().contains(org.springframework.web.bind.annotation.RequestMethod.GET)));
        assertTrue(context.getBeansOfType(DataSource.class).isEmpty());
    }

}
