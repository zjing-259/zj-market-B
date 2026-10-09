package cn.zj.zjmarket.app.config;

import cn.zj.zjmarket.domain.product.adapter.port.IMarketingTrialPort;
import cn.zj.zjmarket.domain.product.service.IMarketingTrialService;
import cn.zj.zjmarket.domain.product.service.IProductService;
import cn.zj.zjmarket.domain.product.service.impl.MarketingTrialService;
import cn.zj.zjmarket.infrastructure.adapter.port.product.DubboMarketingTrial;
import cn.zj.zjmarket.infrastructure.config.properties.RpcSettings;
import cn.zj.zjmarket.infrastructure.gateway.rpc.RpcClientFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.*;
@Configuration(proxyBeanMethods=false)
@ConditionalOnProperty(name="b.trial.enabled",havingValue="true")
public class MarketingTrialConfiguration {
    @Bean(destroyMethod="close") DubboMarketingTrial marketingTrial(RpcSettings rpc,RpcClientFactory factory,
        @Value("${b.product.enabled:false}")boolean enabled,@Value("${b.product.event-producer:}")String producer,@Value("${b.product.event-source:}")String source,@Value("${b.product.event-channel:}")String channel){
        if(!enabled || !producer.equals(rpc.getClientId()) || !source.equals(rpc.getSource()) || !channel.equals(rpc.getChannel()))throw new IllegalArgumentException("Trial and product/RPC scopes must agree");
        return new DubboMarketingTrial(rpc,factory);
    }
    @Bean IMarketingTrialService marketingTrialService(IProductService products,IMarketingTrialPort marketing){return new MarketingTrialService(products,marketing);}
}
