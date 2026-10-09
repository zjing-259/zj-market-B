package cn.zj.zjmarket.infrastructure.gateway.rpc;

import cn.zj.zjmarket.infrastructure.config.properties.RpcSettings;
import org.apache.dubbo.config.ApplicationConfig;
import org.apache.dubbo.config.ReferenceConfig;
import org.apache.dubbo.config.SslConfig;
/** Raw SDK configuration stays here; callers own reference lifecycle. */
public final class RpcClientFactory {
    private final RpcSettings settings;
    public RpcClientFactory(RpcSettings settings) { this.settings = settings; }

    public <T> ReferenceConfig<T> reference(Class<T> type) {
        ReferenceConfig<T> reference = new ReferenceConfig<>();
        reference.setApplication(new ApplicationConfig("zj-market"));
        reference.setInterface(type);
        reference.setUrl(settings.getUrl());
        reference.setVersion(settings.getVersion());
        reference.setGroup(settings.getGroup());
        reference.setRetries(0);
        reference.setInjvm(false);
        reference.setTimeout(settings.getTimeoutMillis());
        SslConfig ssl = new SslConfig();
        ssl.setClientKeyCertChainPath(settings.getClientCertificate());
        ssl.setClientPrivateKeyPath(settings.getClientPrivateKey());
        ssl.setClientTrustCertCollectionPath(settings.getTrustCertificate());
        reference.getApplicationModel().getApplicationConfigManager().setSsl(ssl);
        return reference;
    }
}
