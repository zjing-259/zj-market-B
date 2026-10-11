package cn.zj.zjmarket.verification;

import cn.bugstack.api.v2.*;
import cn.zj.zjmarket.infrastructure.config.properties.MqSettings;
import cn.zj.zjmarket.infrastructure.config.properties.RpcSettings;
import cn.zj.zjmarket.infrastructure.gateway.codec.ContractCodec;
import cn.zj.zjmarket.infrastructure.gateway.mq.MqClientFactory;
import cn.zj.zjmarket.infrastructure.gateway.rpc.RpcClientFactory;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.SecureRandom;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import org.apache.dubbo.config.ReferenceConfig;
import org.apache.dubbo.rpc.RpcContext;
import org.apache.rocketmq.client.consumer.DefaultMQPushConsumer;
import org.apache.rocketmq.client.consumer.listener.ConsumeConcurrentlyStatus;
import org.apache.rocketmq.client.consumer.listener.MessageListenerConcurrently;
import org.apache.rocketmq.client.exception.MQBrokerException;
import org.apache.rocketmq.client.producer.DefaultMQProducer;
import org.apache.rocketmq.client.producer.SendStatus;
import org.apache.rocketmq.common.message.Message;
import org.apache.rocketmq.common.message.MessageExt;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.ExitCodeGenerator;
import org.springframework.boot.SpringBootVersion;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;
/** Opt-in local interoperability check, not a business consumer or durable Inbox. */
@Component
@ConditionalOnProperty(name = "b.verification.enabled", havingValue = "true")
public class EnvironmentProbe implements ApplicationRunner, ExitCodeGenerator {
    private final Environment env;
    private final ContractCodec codec;
    private final RpcSettings rpc;
    private final MqSettings mq;
    private final RpcClientFactory rpcFactory;
    private final MqClientFactory mqFactory;
    private final Map<String, Object> report = new LinkedHashMap<>();
    private int exitCode = 1;

    public EnvironmentProbe(Environment env, ContractCodec codec, RpcSettings rpc, MqSettings mq,
                            RpcClientFactory rpcFactory, MqClientFactory mqFactory) {
        this.env = env; this.codec = codec; this.rpc = rpc; this.mq = mq;
        this.rpcFactory = rpcFactory; this.mqFactory = mqFactory;
    }
    private static void require(boolean passed, String check) {
        if (!passed) throw new IllegalStateException("Check failed: " + check);
    }
    private String setting(String name, String fallback) { return env.getProperty(name, fallback); }
    private String source() { return rpc.getSource(); }
    private String channel() { return rpc.getChannel(); }
    private String group() { return rpc.getGroup(); }
    private String resultTopic() { return mq.getResultTopic(); }
    private String productTopic() { return mq.getProductTopic(); }

    @Override public void run(ApplicationArguments args) throws Exception {
        report.put("javaVersion", System.getProperty("java.version"));
        report.put("javaHome", System.getProperty("java.home"));
        report.put("springBoot", SpringBootVersion.getVersion());
        report.put("dubbo", org.apache.dubbo.common.Version.getVersion());
        report.put("rocketmq", org.apache.rocketmq.common.MQVersion.getVersionDesc(org.apache.rocketmq.common.MQVersion.CURRENT_VERSION));
        report.put("netty", io.netty.util.Version.identify().get("netty-common").artifactVersion());
        report.put("jackson2", com.fasterxml.jackson.databind.cfg.PackageVersion.VERSION.toString());
        report.put("jackson3", tools.jackson.databind.cfg.PackageVersion.VERSION.toString());
        report.put("contract", "cn.bugstack:group-buy-market-contract:1.0-SNAPSHOT");
        report.put("pid", ProcessHandle.current().pid());
        report.put("startedAt", Instant.now().toString());
        report.put("stage", "configuration");
        try {
            require(Runtime.version().feature() == 21, "Actual runtime must be JDK 21");
            require("dev".equals(setting("b.verification.environment", "dev")), "Probe uses isolated local dev only");
            int ownedPort=Integer.parseInt(System.getenv().getOrDefault("B_PROBE_RPC_PORT","50051"));
            require(ownedPort>=1024&&ownedPort<=65535&&("tri://127.0.0.1:"+ownedPort+"?ssl-enabled=true").equals(rpc.getUrl()), "Explicit local TLS provider");
            require(source().equals(mq.getSource()) && channel().equals(mq.getChannel())
                    && rpc.getClientId().equals(mq.getProducerId()), "RPC/MQ authorization scope must agree");
            verify();
            report.put("status", "PASSED");
            exitCode = 0;
        } catch (Exception | LinkageError failure) {
            report.put("status", "FAILED");
            report.put("errorType", failure.getClass().getName());
            List<String> causes = new ArrayList<>();
            for (Throwable cause = failure; cause != null; cause = cause.getCause()) causes.add(cause.getClass().getName());
            report.put("causeTypes", causes);
            // Keep credentials/body/SDK exception text out of the portable report.
        } finally {
            Path output = Path.of(setting("b.verification.report", "target/environment-probe/report.json"));
            Files.createDirectories(output.toAbsolutePath().getParent());
            Files.write(output, codec.encode(report));
            System.out.println("B environment probe: " + report.get("status") + "; stage=" + report.get("stage"));
        }
    }

    private void verify() throws Exception {
        ReferenceConfig<IntegrationService> reference = rpcFactory.reference(IntegrationService.class);
        DefaultMQProducer producer = null;
        DefaultMQPushConsumer consumer = null;
        try {
            report.put("stage", "rpc-tls-query");
            IntegrationService service = reference.get();
            String eventId = "b01-" + UUID.randomUUID();
            require("NOT_FOUND".equals(query(service, eventId, true).getCode()), "Signed query reaches A");
            report.put("signedQuery", "NOT_FOUND");

            report.put("stage", "rpc-auth-rejection");
            require("AUTH_INVALID".equals(query(service, eventId, false).getCode()), "Bad signature rejected");
            report.put("invalidRpcSignature", "AUTH_INVALID");

            report.put("stage", "mq-connect-subscribe");
            producer = mqFactory.producer("B_ENV_PROBE_" + UUID.randomUUID());
            producer.start();
            CompletableFuture<Map<String, Object>> received = new CompletableFuture<>();
            consumer = mqFactory.resultConsumer();
            consumer.subscribe(resultTopic(), "EVENT_PROCESSING_RESULT");
            consumer.registerMessageListener((MessageListenerConcurrently) (messages, context) -> {
                for (MessageExt message : messages) {
                    try {
                        EventEnvelope envelope = codec.decode(message.getBody(), EventEnvelope.class);
                        if (!eventId.equals(envelope.getCorrelationId())) continue;
                        Map<String, Object> payload = verifyResult(message, envelope, eventId);
                        received.complete(payload);
                    } catch (Exception invalid) {
                        received.completeExceptionally(new IllegalStateException("Result verification failed"));
                        return ConsumeConcurrentlyStatus.RECONSUME_LATER;
                    }
                }
                return ConsumeConcurrentlyStatus.CONSUME_SUCCESS;
            });
            consumer.start();
            long assignedBy = System.nanoTime() + TimeUnit.SECONDS.toNanos(20);
            while (consumer.getDefaultMQPushConsumerImpl().getRebalanceImpl().getProcessQueueTable().isEmpty()) {
                require(System.nanoTime() < assignedBy, "Consumer assigned authorized result queues");
                Thread.sleep(200);
            }
            report.put("mqSubscription", "AUTHORIZED");

            report.put("stage", "mq-product-publish");
            ProductSnapshotChanged product = new ProductSnapshotChanged();
            String goodsId = "b01-" + UUID.randomUUID();
            product.setGoodsId(goodsId); product.setGoodsName("B-01 环境验证商品");
            product.setProductVersion("1"); product.setOriginalPrice("100.00");
            product.setCurrency("CNY"); product.setSaleStatus("ON_SALE");
            EventEnvelope event = new EventEnvelope();
            event.setEventId(eventId); event.setEventType("PRODUCT_SNAPSHOT_CHANGED"); event.setSchemaVersion(1);
            event.setProducer(rpc.getClientId()); event.setSource(source()); event.setChannel(channel());
            event.setOccurredAt(DateTimeFormatter.ofPattern("uuuu-MM-dd'T'HH:mm:ss.SSS'Z'")
                    .withZone(ZoneOffset.UTC).format(Instant.now()));
            event.setPayload(product);
            byte[] body = codec.encode(event);
            Message message = new Message(productTopic(), event.getEventType(), eventId, body);
            message.putUserProperty("source", source()); message.putUserProperty("channel", channel());
            message.putUserProperty("keyId", mq.getBKeyId());
            message.putUserProperty("signature", ContractCodec.hmac(mq.getBSecret(),
                    productTopic() + "\n" + ContractCodec.sha256(body)));
            require(producer.send(message, 10000).getSendStatus() == SendStatus.SEND_OK, "Broker confirmed product send");
            report.put("mqPublish", "SEND_OK");
            report.put("eventId", eventId); report.put("goodsId", goodsId);

            report.put("stage", "mq-result-receive");
            Map<String, Object> result = received.get(45, TimeUnit.SECONDS);
            require(goodsId.equals(result.get("goodsId")), "Result payload goodsId round trip");
            require("1".equals(result.get("currentVersion")) && Boolean.TRUE.equals(result.get("applied")),
                    "Result payload version and boolean serialization");
            require("ON_SALE".equals(result.get("saleStatus")), "Result payload saleStatus");
            report.put("mqResult", "VERIFIED_APPLIED");

            report.put("stage", "rpc-durable-result");
            RpcResult<EventProcessingResult> persisted = query(service, eventId, true);
            require("0000".equals(persisted.getCode()) && persisted.getData() != null
                    && "PROCESSED".equals(persisted.getData().getProcessingStatus())
                    && "APPLIED".equals(persisted.getData().getOutcome())
                    && "0000".equals(persisted.getData().getCode())
                    && "PRODUCT_SNAPSHOT_CHANGED".equals(persisted.getData().getEventType()),
                    "A durable result confirmed via RPC");
            report.put("durableResultQuery", "PROCESSED_APPLIED");

            report.put("stage", "mq-acl-rejection");
            try {
                producer.send(new Message(mq.getTeamTopic(), "TEAM_COMPLETED",
                        UUID.randomUUID().toString(), "{}".getBytes(java.nio.charset.StandardCharsets.UTF_8)), 10000);
                throw new IllegalStateException("B published to A-only topic");
            } catch (org.apache.rocketmq.client.exception.MQClientException | MQBrokerException denied) {
                Throwable cause = denied;
                boolean explicit = false;
                while (cause != null) {
                    if (cause instanceof MQBrokerException broker && broker.getResponseCode() == 1
                            && broker.getErrorMessage().toLowerCase(Locale.ROOT).contains("permission")) explicit = true;
                    cause = cause.getCause();
                }
                require(explicit, "Explicit Broker permission rejection");
                report.put("mqForbiddenPublish", "PERMISSION_DENIED");
            }
            report.put("stage", "complete");
        } finally {
            if (consumer != null) consumer.shutdown();
            if (producer != null) producer.shutdown();
            reference.destroy();
            reference.getApplicationModel().destroy();
        }
    }

    private RpcResult<EventProcessingResult> query(IntegrationService service, String eventId, boolean valid) throws Exception {
        EventResultQueryRequest dto = new EventResultQueryRequest();
        dto.setSource(source()); dto.setChannel(channel()); dto.setEventId(eventId);
        String timestamp = Long.toString(System.currentTimeMillis()), requestId = UUID.randomUUID().toString();
        byte[] random = new byte[24]; new SecureRandom().nextBytes(random);
        String nonce = Base64.getUrlEncoder().withoutPadding().encodeToString(random);
        String client = rpc.getClientId(), key = rpc.getKeyId();
        String text = String.join("\n", client, key, timestamp, nonce, requestId,
                IntegrationService.class.getName(), "queryEventResult", "2.0.0", group(),
                ContractCodec.sha256(codec.encode(dto)));
        Map<String, String> attachments = Map.of("clientId", client, "keyId", key,
                "timestamp", timestamp, "nonce", nonce, "requestId", requestId,
                "signature", valid ? ContractCodec.hmac(rpc.getSecret(), text) : "invalid");
        try {
            attachments.forEach((name, value) -> RpcContext.getClientAttachment().setAttachment(name, value));
            RpcResult<EventProcessingResult> result = service.queryEventResult(dto);
            require(requestId.equals(result.getRequestId()), "RPC requestId preserved");
            return result;
        } finally { RpcContext.getClientAttachment().clearAttachments(); }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> verifyResult(MessageExt message, EventEnvelope event, String eventId) throws Exception {
        require(resultTopic().equals(message.getTopic()), "A result topic");
        require(mq.getAKeyId().equals(message.getProperty("keyId")), "A message keyId");
        require(ContractCodec.validSignature(mq.getASecret(), message.getTopic(),
                message.getBody(), message.getProperty("signature")), "A message HMAC");
        require(mq.getAProducerId().equals(event.getProducer()) && Integer.valueOf(1).equals(event.getSchemaVersion())
                && "EVENT_PROCESSING_RESULT".equals(event.getEventType()), "A envelope identity");
        require(message.getKeys().equals(event.getEventId()) && message.getTags().equals(event.getEventType()),
                "Message key and tag");
        require(source().equals(event.getSource()) && channel().equals(event.getChannel())
                && source().equals(message.getProperty("source")) && channel().equals(message.getProperty("channel")),
                "Result channel authorization");
        Map<String, Object> payload = (Map<String, Object>) event.getPayload();
        require(eventId.equals(payload.get("originalEventId"))
                && "PRODUCT_SNAPSHOT_CHANGED".equals(payload.get("originalEventType"))
                && "APPLIED".equals(payload.get("outcome")) && "0000".equals(payload.get("code")),
                "Result correlation and success code");
        return (Map<String, Object>) payload.get("result");
    }
    @Override public int getExitCode() { return exitCode; }
}
