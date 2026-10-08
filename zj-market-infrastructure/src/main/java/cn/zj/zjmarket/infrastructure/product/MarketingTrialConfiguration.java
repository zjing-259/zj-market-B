package cn.zj.zjmarket.infrastructure.product;
import cn.zj.zjmarket.application.product.*;
import cn.zj.zjmarket.infrastructure.config.RpcSettings;
import cn.zj.zjmarket.infrastructure.integration.rpc.RpcClientFactory;
import org.springframework.context.annotation.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
@Configuration(proxyBeanMethods=false)
@ConditionalOnProperty(name="b.trial.enabled",havingValue="true")
public class MarketingTrialConfiguration {
    @Bean(destroyMethod="close") DubboMarketingTrial marketingTrial(RpcSettings rpc,RpcClientFactory factory,
        @Value("${b.product.enabled:false}")boolean enabled,@Value("${b.product.event-producer:}")String producer,@Value("${b.product.event-source:}")String source,@Value("${b.product.event-channel:}")String channel){
        if(!enabled || !producer.equals(rpc.getClientId()) || !source.equals(rpc.getSource()) || !channel.equals(rpc.getChannel()))throw new IllegalArgumentException("Trial and product/RPC scopes must agree");
        return new DubboMarketingTrial(rpc,factory);
    }
    @Bean MarketingTrialService marketingTrialService(ProductService products,MarketingTrialPort marketing){return new MarketingTrialService(products,marketing);}
}
