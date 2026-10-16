package cn.zj.zjmarket.app.config;
import cn.zj.zjmarket.domain.order.adapter.port.ITeamDiscoveryPort;
import cn.zj.zjmarket.domain.order.service.ITeamDiscoveryService;
import cn.zj.zjmarket.domain.order.service.IOrderService;
import cn.zj.zjmarket.domain.order.service.impl.TeamDiscoveryService;
import cn.zj.zjmarket.domain.product.service.IProductService;
import cn.zj.zjmarket.domain.product.service.IMarketingTrialService;
import cn.zj.zjmarket.domain.inventory.service.IInventoryService;
import cn.zj.zjmarket.infrastructure.adapter.port.order.DubboTeamDiscoveryPort;
import cn.zj.zjmarket.infrastructure.config.properties.RpcSettings;
import cn.zj.zjmarket.infrastructure.gateway.rpc.RpcClientFactory;
import cn.zj.zjmarket.trigger.http.TeamDiscoveryGate;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.*;
import org.springframework.context.annotation.*;
@Configuration(proxyBeanMethods=false)
@ConditionalOnProperty(name="b.team-discovery.enabled",havingValue="true")
public class TeamDiscoveryConfiguration {
 @Bean(destroyMethod="close") ITeamDiscoveryPort teamDiscoveryPort(RpcSettings rpc,RpcClientFactory factory){if(!rpc.isEnabled())throw new IllegalArgumentException("Discovery requires authenticated RPC");return new DubboTeamDiscoveryPort(rpc,factory);}
 @Bean ITeamDiscoveryService teamDiscoveryService(IProductService products,IOrderService orders,IInventoryService stock,IMarketingTrialService trial,ITeamDiscoveryPort port){return new TeamDiscoveryService(products,orders,stock,trial,port);}
 @Bean(destroyMethod="close") TeamDiscoveryGate teamDiscoveryGate(@Value("${b.team-discovery.rate-per-minute:30}")int rate,@Value("${b.team-discovery.max-concurrent:32}")int concurrency){return new TeamDiscoveryGate(rate,concurrency);}
}
