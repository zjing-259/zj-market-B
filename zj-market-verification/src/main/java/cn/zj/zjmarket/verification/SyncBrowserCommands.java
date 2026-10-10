package cn.zj.zjmarket.verification;

import cn.zj.zjmarket.ZjMarketApplication;
import cn.zj.zjmarket.domain.product.adapter.repository.IProductSyncRepository;
import cn.zj.zjmarket.domain.product.service.IProductSyncService;
import cn.zj.zjmarket.infrastructure.adapter.port.product.RocketMqSyncTransport;
import java.nio.file.Files;
import java.nio.file.Path;
import javax.sql.DataSource;
import org.springframework.boot.SpringApplication;

/** Verification-only bounded worker. Every claim is constrained to the owned fixture event. */
public final class SyncBrowserCommands {
    public static int run() { return run(false); }
    public static int run(boolean trial) {
        try {
            SyncCommands.guard();
            var scope = trial ? Path.of(SyncCommands.env("B_TRIAL_BROWSER_SCOPE")) : null;
            var fixture = trial ? null : SyncCommands.JSON.readTree(Files.readAllBytes(Path.of(SyncCommands.env("B_SYNC_WORK"), "browser-fixture.json")));
            String eventId = trial ? null : fixture.required("eventId").asText();
            try (var ctx = new SpringApplication(ZjMarketApplication.class).run(
                    "--server.port=18092", "--b.identity.enabled=true", "--b.product.enabled=true",
                    "--b.inventory.enabled=false", "--b.order.enabled=false", "--b.trade.enabled=false",
                    "--b.trial.enabled=" + trial, "--b.sync.enabled=true", "--b.sync.scheduler-enabled=false",
                    "--b.infrastructure.database.enabled=true", "--b.infrastructure.rpc.enabled=true",
                    "--b.infrastructure.mq.enabled=true")) {
                var store = ctx.getBean(IProductSyncRepository.class);
                if (!trial) {
                    var owned = store.event(eventId);
                    SyncCommands.check(owned != null && owned.goodsId().equals(fixture.required("goodsId").asText())
                            && owned.bodyHash().equals(fixture.required("bodyHash").asText()), "owned browser event identity");
                }
                var allowed = new java.util.LinkedHashMap<String, String>();
                var service = ctx.getBean(IProductSyncService.class);
                var db = ctx.getBean(DataSource.class);
                ctx.getBean(RocketMqSyncTransport.class).startConsumer(8, false);
                long deadline = System.nanoTime() + java.util.concurrent.TimeUnit.MINUTES.toNanos(5);
                while (System.nanoTime() < deadline) {
                    // Wait for both real page resume actions so the intermediate pause is deterministic.
                    // This gate changes only verification scheduling; claim, signatures, transport and results are real.
                    if (trial) {
                        var entries = SyncCommands.JSON.readTree(Files.readAllBytes(scope));
                        SyncCommands.check(entries.isArray() && entries.size() <= 20, "bounded owned trial events");
                        for (var entry : entries) {
                            String id = entry.required("eventId").asText(), goodsId = entry.required("goodsId").asText();
                            java.util.UUID.fromString(id);
                            var owned = store.event(id);
                            SyncCommands.check(owned != null && owned.goodsId().equals(goodsId), "owned trial event association");
                            String previous = allowed.putIfAbsent(id, owned.bodyHash());
                            SyncCommands.check(previous == null || previous.equals(owned.bodyHash()), "owned trial immutable body");
                            service.publishOne(id);
                            service.queryOne(id);
                        }
                        Files.writeString(scope.resolveSibling("browser-scoped-events.json"), SyncCommands.JSON.writeValueAsString(java.util.Map.of(
                                "status", "PASSED", "mode", "verification-owned-events/real-service/A/MQ", "events", allowed)));
                    } else if (SyncCommands.count(db, "SELECT COUNT(*) FROM b_sync_audit WHERE event_id=? AND action='RETRY'", eventId) >= 2) {
                        service.publishOne(eventId);
                        service.queryOne(eventId);
                    }
                    Thread.sleep(200);
                }
            }
            return 0;
        } catch (Exception e) {
            System.err.println("Scoped sync browser verification failed: " + e.getClass().getSimpleName());
            return 1;
        }
    }
}
