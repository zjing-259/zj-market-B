package cn.zj.zjmarket.infrastructure.gateway.mq;

import cn.zj.zjmarket.infrastructure.config.properties.MqSettings;
import org.apache.rocketmq.acl.common.AclClientRPCHook;
import org.apache.rocketmq.acl.common.SessionCredentials;
import org.apache.rocketmq.client.consumer.DefaultMQPushConsumer;
import org.apache.rocketmq.client.consumer.rebalance.AllocateMessageQueueAveragely;
import org.apache.rocketmq.client.producer.DefaultMQProducer;
import org.apache.rocketmq.common.consumer.ConsumeFromWhere;
/** SDK construction only. No connection/publish occurs until the caller explicitly starts a client. */
public final class MqClientFactory {
    private final MqSettings settings;
    public MqClientFactory(MqSettings settings) { this.settings = settings; }
    private AclClientRPCHook credentials() {
        return new AclClientRPCHook(new SessionCredentials(settings.getAccessKey(), settings.getSecretKey()));
    }
    public DefaultMQProducer producer(String group) {
        DefaultMQProducer producer = new DefaultMQProducer(group, credentials());
        producer.setNamesrvAddr(settings.getNameserver());
        producer.setUseTLS(settings.isUseTls());
        producer.setRetryTimesWhenSendFailed(0);
        producer.setSendMsgTimeout(settings.getSendTimeoutMillis());
        return producer;
    }
    public DefaultMQPushConsumer resultConsumer() {
        DefaultMQPushConsumer consumer = new DefaultMQPushConsumer(
                settings.getResultConsumerGroup(), credentials(), new AllocateMessageQueueAveragely());
        consumer.setNamesrvAddr(settings.getNameserver());
        consumer.setUseTLS(settings.isUseTls());
        consumer.setConsumeFromWhere(ConsumeFromWhere.CONSUME_FROM_LAST_OFFSET);
        consumer.setConsumeThreadMin(1);
        consumer.setConsumeThreadMax(1);
        return consumer;
    }
}
