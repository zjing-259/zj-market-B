package cn.zj.zjmarket;

import cn.zj.zjmarket.infrastructure.config.InfrastructureConfiguration;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Import;

@SpringBootApplication(scanBasePackages = "cn.zj.zjmarket.trigger")
@Import({cn.zj.zjmarket.infrastructure.product.MarketingTrialConfiguration.class, InfrastructureConfiguration.class, cn.zj.zjmarket.infrastructure.product.SyncConfiguration.class, cn.zj.zjmarket.infrastructure.product.ProductConfiguration.class, cn.zj.zjmarket.infrastructure.identity.IdentityConfiguration.class, cn.zj.zjmarket.web.IdentityWebConfiguration.class})
public class ZjMarketApplication {
    public static void main(String[] args) {
        SpringApplication.run(ZjMarketApplication.class, args);
    }
}
