package cn.zj.zjmarket.verification;

import cn.zj.zjmarket.ZjMarketApplication;
import org.springframework.boot.SpringApplication;
/** Separate executable using the real B bootstrap and infrastructure. */
public final class ZjMarketVerificationApplication {
    public static void main(String[] args) {
        if(args.length==1 && args[0].equals("--trial-browser")){System.exit(SyncBrowserCommands.run(true));return;}
        if(args.length==1 && args[0].equals("--sync-browser")){System.exit(SyncBrowserCommands.run());return;}
        if(args.length==1 && args[0].equals("--joint-faults")){System.exit(JointFaultCommands.run());return;}
        if(args.length==1 && args[0].equals("--closes")){System.exit(CloseCommands.run());return;}
        if(args.length==1 && args[0].equals("--trades")){System.exit(TradeCommands.run());return;}
        if(args.length==1 && args[0].equals("--orders-browser")){System.exit(OrderCommands.browserServer());return;}
        if(args.length==1 && args[0].equals("--orders")){System.exit(OrderCommands.run());return;}
        if(args.length==1 && args[0].equals("--inventory")){System.exit(InventoryCommands.run());return;}
        if(args.length==2 && args[0].equals("--b03-readiness")){System.exit(B03ReadinessCommands.run(args[1]));return;}
        if(args.length==2 && args[0].equals("--trial")){System.exit(TrialCommands.run(args[1]));return;}
        if(args.length>=2 && args[0].equals("--sync")){System.exit(SyncCommands.run(args[1],args.length==3?args[2]:null));return;}
        if(args.length==1 && args[0].equals("--products")){System.exit(ProductCommands.run());return;}
        if(args.length==2 && args[0].equals("--identity")){System.exit(IdentityCommands.run(args[1]));return;}
        if (args.length > 0 && args[0].equals("--database")) {
            if (args.length != 2) {
                System.err.println("Usage: --database migrate|verify");
                System.exit(1);
                return;
            }
            System.exit(DatabaseCommands.run(args[1]));
            return;
        }
        SpringApplication application = new SpringApplication(ZjMarketApplication.class, EnvironmentProbe.class);
        application.setAdditionalProfiles("environment-probe");
        var context = application.run(args);
        System.exit(SpringApplication.exit(context));
    }
}
