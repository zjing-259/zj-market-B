package cn.zj.zjmarket.td05;

import cn.zj.zjmarket.infrastructure.adapter.port.order.DubboTeamDiscoveryPort;
import cn.zj.zjmarket.infrastructure.config.properties.RpcSettings;
import cn.zj.zjmarket.infrastructure.gateway.rpc.RpcClientFactory;
import java.io.FileInputStream;
import java.util.Properties;
import java.util.UUID;

/** Direct signed A RPC readiness probe; no B web controller or feature flag. */
public final class Td05RpcProbe {
    private static Properties load(String path) throws Exception {
        Properties p=new Properties();
        try(FileInputStream in=new FileInputStream(path)){p.load(in);}
        return p;
    }
    public static void main(String[] args) throws Exception {
        if(args.length!=4)throw new IllegalArgumentException("goods activity productVersion userId required");
        Properties app=load("/private/config/b.properties");
        Properties privateProps=load("/private/runtime/b.properties");
        RpcSettings s=new RpcSettings();
        s.setEnabled(true);
        s.setUrl(app.getProperty("b.infrastructure.rpc.url"));
        s.setGroup(app.getProperty("b.infrastructure.rpc.group"));
        s.setVersion("2.0.0");
        s.setClientId(app.getProperty("b.infrastructure.rpc.client-id"));
        s.setKeyId(app.getProperty("b.infrastructure.rpc.key-id"));
        s.setSource(app.getProperty("b.infrastructure.rpc.source"));
        s.setChannel(app.getProperty("b.infrastructure.rpc.channel"));
        s.setSecret(privateProps.getProperty("b.infrastructure.rpc.secret"));
        s.setClientCertificate("/private/runtime/rpc-client.pem");
        s.setClientPrivateKey("/private/runtime/rpc-client-key.pem");
        s.setTrustCertificate("/private/runtime/rpc-server-ca.pem");
        s.setTimeoutMillis(3000);
        s.validate();
        try(DubboTeamDiscoveryPort port=new DubboTeamDiscoveryPort(s,new RpcClientFactory(s))){
            var page=port.list(args[3],args[0],args[1],args[2],2,3,null,UUID.randomUUID().toString());
            if(!"AVAILABLE".equals(page.state())&& !"NO_OFFER".equals(page.state()))
                throw new IllegalStateException("A discovery returned unexpected state: "+page.state());
            System.out.println("TD05_A_RPC_READY "+page.state());
        }finally{
            org.apache.dubbo.rpc.model.ApplicationModel.defaultModel().destroy();
        }
    }
}
