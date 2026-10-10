package cn.zj.zjmarket;

import cn.zj.zjmarket.app.config.IdentityConfiguration;
import cn.zj.zjmarket.app.config.IdentityWebConfiguration;
import cn.zj.zjmarket.app.config.InfrastructureConfiguration;
import cn.zj.zjmarket.app.config.MarketingTrialConfiguration;
import cn.zj.zjmarket.app.config.ProductConfiguration;
import cn.zj.zjmarket.app.config.SyncConfiguration;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Import;
@SpringBootApplication(scanBasePackages = "cn.zj.zjmarket.trigger")
@Import({cn.zj.zjmarket.app.config.SettlementConfiguration.class, cn.zj.zjmarket.app.config.PaymentConfiguration.class, cn.zj.zjmarket.app.config.TradeConfiguration.class, cn.zj.zjmarket.app.config.OrderConfiguration.class, cn.zj.zjmarket.app.config.InventoryConfiguration.class, cn.zj.zjmarket.app.config.MarketingTrialConfiguration.class, InfrastructureConfiguration.class, cn.zj.zjmarket.app.config.SyncConfiguration.class, cn.zj.zjmarket.app.config.ProductConfiguration.class, cn.zj.zjmarket.app.config.IdentityConfiguration.class, cn.zj.zjmarket.app.config.IdentityWebConfiguration.class})
public class ZjMarketApplication {
    public static void main(String[] args) {
        SpringApplication.run(ZjMarketApplication.class, args);
    }
}
