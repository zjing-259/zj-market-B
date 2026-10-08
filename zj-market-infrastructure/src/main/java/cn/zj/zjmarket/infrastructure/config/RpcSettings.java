package cn.zj.zjmarket.infrastructure.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/** Bound external configuration. Deliberately no generated toString containing credentials. */
@ConfigurationProperties("b.infrastructure.rpc")
public class RpcSettings {
    private boolean enabled = false;
    private String url;
    private String version = "2.0.0";
    private String group;
    private String clientId;
    private String keyId;
    private String secret;
    private String source;
    private String channel;
    private String clientCertificate;
    private String clientPrivateKey;
    private String trustCertificate;
    private int timeoutMillis = 10000;
    public boolean isEnabled() { return enabled; }
    public void setEnabled(boolean value) { enabled = value; }
    public String getUrl() { return url; }
    public void setUrl(String value) { url = value; }
    public String getVersion() { return version; }
    public void setVersion(String value) { version = value; }
    public String getGroup() { return group; }
    public void setGroup(String value) { group = value; }
    public String getClientId() { return clientId; }
    public void setClientId(String value) { clientId = value; }
    public String getKeyId() { return keyId; }
    public void setKeyId(String value) { keyId = value; }
    public String getSecret() { return secret; }
    public void setSecret(String value) { secret = value; }
    public String getSource() { return source; }
    public void setSource(String value) { source = value; }
    public String getChannel() { return channel; }
    public void setChannel(String value) { channel = value; }
    public String getClientCertificate() { return clientCertificate; }
    public void setClientCertificate(String value) { clientCertificate = value; }
    public String getClientPrivateKey() { return clientPrivateKey; }
    public void setClientPrivateKey(String value) { clientPrivateKey = value; }
    public String getTrustCertificate() { return trustCertificate; }
    public void setTrustCertificate(String value) { trustCertificate = value; }
    public int getTimeoutMillis() { return timeoutMillis; }
    public void setTimeoutMillis(int value) { timeoutMillis = value; }
    public void validate() {
        ConfigurationChecks.required(url, "rpc.url");
        ConfigurationChecks.required(group, "rpc.group");
        ConfigurationChecks.required(clientId, "rpc.client-id");
        ConfigurationChecks.required(keyId, "rpc.key-id");
        ConfigurationChecks.required(secret, "rpc.secret");
        ConfigurationChecks.required(source, "rpc.source");
        ConfigurationChecks.required(channel, "rpc.channel");
        ConfigurationChecks.required(clientCertificate, "rpc.client-certificate");
        ConfigurationChecks.required(clientPrivateKey, "rpc.client-private-key");
        ConfigurationChecks.required(trustCertificate, "rpc.trust-certificate");
        ConfigurationChecks.require("2.0.0".equals(version), "Unsupported RPC service version");
        java.net.URI address = java.net.URI.create(url);
        ConfigurationChecks.require("tri".equals(address.getScheme()) && address.getHost() != null
                && address.getRawQuery() != null
                && java.util.Arrays.asList(address.getRawQuery().split("&")).contains("ssl-enabled=true"),
                "RPC requires an explicit TLS Triple URL");
        ConfigurationChecks.require(timeoutMillis > 0, "RPC timeout must be positive");
    }
}
