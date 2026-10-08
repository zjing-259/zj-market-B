package cn.zj.zjmarket.infrastructure.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/** Bound external configuration. Deliberately no generated toString containing credentials. */
@ConfigurationProperties("b.infrastructure.mq")
public class MqSettings {
    private boolean enabled = false;
    private String nameserver;
    private String accessKey;
    private String secretKey;
    private String producerId;
    private String bKeyId;
    private String bSecret;
    private String aProducerId = "group-buy-market";
    private String aKeyId;
    private String aSecret;
    private String source;
    private String channel;
    private String productTopic;
    private String resultTopic;
    private String teamTopic;
    private String resultConsumerGroup;
    private boolean useTls = true;
    private boolean allowPlaintextLoopback = false;
    private int sendTimeoutMillis = 10000;
    public boolean isEnabled() { return enabled; }
    public void setEnabled(boolean value) { enabled = value; }
    public String getNameserver() { return nameserver; }
    public void setNameserver(String value) { nameserver = value; }
    public String getAccessKey() { return accessKey; }
    public void setAccessKey(String value) { accessKey = value; }
    public String getSecretKey() { return secretKey; }
    public void setSecretKey(String value) { secretKey = value; }
    public String getProducerId() { return producerId; }
    public void setProducerId(String value) { producerId = value; }
    public String getBKeyId() { return bKeyId; }
    public void setBKeyId(String value) { bKeyId = value; }
    public String getBSecret() { return bSecret; }
    public void setBSecret(String value) { bSecret = value; }
    public String getAProducerId() { return aProducerId; }
    public void setAProducerId(String value) { aProducerId = value; }
    public String getAKeyId() { return aKeyId; }
    public void setAKeyId(String value) { aKeyId = value; }
    public String getASecret() { return aSecret; }
    public void setASecret(String value) { aSecret = value; }
    public String getSource() { return source; }
    public void setSource(String value) { source = value; }
    public String getChannel() { return channel; }
    public void setChannel(String value) { channel = value; }
    public String getProductTopic() { return productTopic; }
    public void setProductTopic(String value) { productTopic = value; }
    public String getResultTopic() { return resultTopic; }
    public void setResultTopic(String value) { resultTopic = value; }
    public String getTeamTopic() { return teamTopic; }
    public void setTeamTopic(String value) { teamTopic = value; }
    public String getResultConsumerGroup() { return resultConsumerGroup; }
    public void setResultConsumerGroup(String value) { resultConsumerGroup = value; }
    public boolean isUseTls() { return useTls; }
    public void setUseTls(boolean value) { useTls = value; }
    public boolean isAllowPlaintextLoopback() { return allowPlaintextLoopback; }
    public void setAllowPlaintextLoopback(boolean value) { allowPlaintextLoopback = value; }
    public int getSendTimeoutMillis() { return sendTimeoutMillis; }
    public void setSendTimeoutMillis(int value) { sendTimeoutMillis = value; }
    public void validate() {
        ConfigurationChecks.required(nameserver, "mq.nameserver");
        ConfigurationChecks.required(accessKey, "mq.access-key");
        ConfigurationChecks.required(secretKey, "mq.secret-key");
        ConfigurationChecks.required(producerId, "mq.producer-id");
        ConfigurationChecks.required(bKeyId, "mq.b-key-id");
        ConfigurationChecks.required(bSecret, "mq.b-secret");
        ConfigurationChecks.required(aProducerId, "mq.a-producer-id");
        ConfigurationChecks.required(aKeyId, "mq.a-key-id");
        ConfigurationChecks.required(aSecret, "mq.a-secret");
        ConfigurationChecks.required(source, "mq.source");
        ConfigurationChecks.required(channel, "mq.channel");
        ConfigurationChecks.required(productTopic, "mq.product-topic");
        ConfigurationChecks.required(resultTopic, "mq.result-topic");
        ConfigurationChecks.required(teamTopic, "mq.team-topic");
        ConfigurationChecks.required(resultConsumerGroup, "mq.result-consumer-group");
        ConfigurationChecks.require(sendTimeoutMillis > 0, "MQ timeout must be positive");
        if (!useTls) {
            boolean local = java.util.Arrays.stream(nameserver.split(";"))
                    .allMatch(address -> address.matches("(127\\.0\\.0\\.1|localhost):[0-9]+"));
            ConfigurationChecks.require(allowPlaintextLoopback && local,
                    "Plaintext MQ is allowed only by explicit loopback development configuration");
        }
    }
}
