package cn.zj.zjmarket.verification;
import cn.zj.zjmarket.ZjMarketApplication;
import cn.zj.zjmarket.infrastructure.gateway.codec.ContractCodec;
import org.springframework.boot.SpringApplication;
import org.springframework.jdbc.core.JdbcTemplate;
import javax.sql.DataSource;
import java.nio.file.*;
import java.util.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import static cn.zj.zjmarket.verification.ProductCommands.*;
/** Read-only isolated-database audit. No claims, retries, payment/refund calls or writes. */
final class B04HandoffCommands {
 static int run(){try{
  check(env("B_DATABASE_SCOPE").equals("b02-test")&&env("B_DATABASE_USERNAME").equals("zj_market_b02_test_app")&&env("B_DATABASE_URL").matches("^jdbc:mysql://[^/]+/zj_market_b02_test(?:\\?.*)?$"),"exact isolated handoff database");
  var report=new LinkedHashMap<String,Object>();report.put("status","RUNNING");
  try(var ctx=new SpringApplication(ZjMarketApplication.class).run("--spring.main.web-application-type=none","--b.identity.enabled=false","--b.product.enabled=false","--b.inventory.enabled=false","--b.order.enabled=false","--b.trade.enabled=false","--b.payment.enabled=false","--b.trade.events-enabled=false","--b.trial.enabled=false","--b.sync.enabled=false","--b.infrastructure.database.enabled=true","--b.infrastructure.rpc.enabled=false","--b.infrastructure.mq.enabled=false")){
   var db=new JdbcTemplate(ctx.getBean(DataSource.class));var failures=new LinkedHashMap<String,Long>();
   String refunded="EXISTS(SELECT 1 FROM b_refund rf JOIN b_refund_release rr ON rr.refund_id=rf.refund_id JOIN b_inventory_ledger l ON l.ledger_id=rr.ledger_id JOIN b_market_order ro ON ro.order_id=rr.order_id WHERE rf.payment_id=p.payment_id AND rf.order_id=p.order_id AND rf.funds_status='SUCCEEDED' AND rf.amount=p.amount AND rf.currency=p.currency AND rr.payment_id=p.payment_id AND rr.order_id=p.order_id AND rr.success_hash=rf.success_hash AND rr.eligibility_hash=rf.eligibility_proof_hash AND rr.refund_fact_version=rf.fact_version AND ro.business_status='CLOSED' AND l.order_id=p.order_id AND l.kind='RELEASE' AND l.after_available=l.before_available+1 AND l.after_reserved=l.before_reserved-1 AND l.after_sold=l.before_sold AND ((rr.outcome='RELEASED' AND ro.close_basis='FULL_REFUND_CONFIRMED' AND ro.closed_at_ms=rr.released_at_ms) OR (rr.outcome='ALREADY_RELEASED' AND ro.close_basis IN ('LOCAL_NEVER_DISPATCHED','A_CONFIRMED'))))";
   var queries=Map.of(
    "multipleChannelSuccess","SELECT COUNT(*) FROM (SELECT payment_id FROM b_sim_attempt WHERE state='SUCCEEDED' GROUP BY payment_id HAVING COUNT(*)>1) x",
    "successOrUnknownReleased","SELECT COUNT(*) FROM b_payment p JOIN b_inventory_reservation r ON r.order_id=p.order_id WHERE r.state='RELEASED' AND (p.funds_state='UNKNOWN' OR (p.funds_state='SUCCEEDED' AND NOT "+refunded+"))",
    "fulfillmentWithoutConfirmation","SELECT COUNT(*) FROM b_fulfillment f JOIN b_payment p ON p.payment_id=f.payment_id JOIN b_market_order o ON o.order_id=f.order_id JOIN b_inventory_reservation r ON r.order_id=f.order_id WHERE p.funds_state<>'SUCCEEDED' OR p.a_acceptance<>'ACCEPTED' OR o.business_status<>'GROUP_COMPLETED' OR r.state<>'CONFIRMED' OR (SELECT COUNT(*) FROM b_inventory_ledger l WHERE l.order_id=f.order_id AND l.kind='CONFIRM')<>1",
    "deferredRefundLostHoldOrGuard","SELECT COUNT(*) FROM b_trade_work w JOIN b_payment p ON p.payment_id=w.payment_id JOIN b_market_order o ON o.order_id=w.order_id JOIN b_inventory_reservation r ON r.order_id=o.order_id LEFT JOIN b_purchase_guard g ON g.user_id=o.user_id AND g.goods_id=o.goods_id WHERE w.kind='REFUND_OBLIGATION' AND w.state<>'DONE' AND (r.state<>'HELD' OR g.active_order_id IS NULL OR g.active_order_id<>o.order_id) AND NOT "+refunded,
    "completedWithoutFulfillment","SELECT COUNT(*) FROM b_market_order o LEFT JOIN b_fulfillment f ON f.order_id=o.order_id WHERE o.business_status='GROUP_COMPLETED' AND f.order_id IS NULL"
   );
   for(var q:queries.entrySet())failures.put(q.getKey(),db.queryForObject(q.getValue(),Long.class));
   long badHashes=0;for(var row:db.queryForList("SELECT evidence,evidence_hash FROM b_trade_work"))if(!ContractCodec.sha256((byte[])row.get("evidence")).equals(row.get("evidence_hash")))badHashes++;
   failures.put("workEvidenceHashMismatch",badHashes);
   long releaseHashes=0;var codec=new ObjectMapper();for(var release:db.queryForList("SELECT * FROM b_refund_release")){byte[] raw=(byte[])release.get("proof");boolean valid=ContractCodec.sha256(raw).equals(release.get("proof_hash"));var proof=codec.readTree(raw);for(var key:Map.of("refundId","refund_id","orderId","order_id","paymentId","payment_id","ledgerId","ledger_id","outcome","outcome","eligibilityHash","eligibility_hash","successHash","success_hash").entrySet())valid&=proof.path(key.getKey()).asText().equals(release.get(key.getValue()));valid&=proof.path("refundVersion").asLong()==((Number)release.get("refund_fact_version")).longValue()&&proof.path("releasedAt").asLong()==((Number)release.get("released_at_ms")).longValue();if(!valid)releaseHashes++;}failures.put("refundReleaseProofMismatch",releaseHashes);
   report.put("violations",failures);
   report.put("workByKindAndState",db.queryForList("SELECT kind,state,COUNT(*) AS count FROM b_trade_work GROUP BY kind,state ORDER BY kind,state"));
   report.put("fundsByState",db.queryForList("SELECT funds_state,a_acceptance,COUNT(*) AS count FROM b_payment GROUP BY funds_state,a_acceptance"));
   report.put("missingLocalWork",db.queryForObject("SELECT COUNT(*) FROM b_trade_work w LEFT JOIN b_market_order o ON o.order_id=w.order_id WHERE w.order_id IS NOT NULL AND o.order_id IS NULL",Long.class));
   report.put("pendingFulfillment",db.queryForObject("SELECT COUNT(*) FROM b_fulfillment WHERE status='PENDING'",Long.class));
   report.put("reconciliationAndRefundExecution","IMPLEMENTED_THROUGH_B055_PROOF_AWARE_AUDIT");report.put("scope","accumulated isolated test database; controlled and actual-A fixtures, not production backlog");
   report.put("status",failures.values().stream().allMatch(n->n==0)?"PASSED":"FAILED");
   new ObjectMapper().writerWithDefaultPrettyPrinter().writeValue(Path.of(env("B_PAYMENT_WORK"),"snapshot.json").toFile(),report);
   check(report.get("status").equals("PASSED"),"handoff invariants");
  }return 0;
 }catch(Exception e){System.err.println("B04 handoff audit failed: "+e.getClass().getSimpleName());return 1;}}
}
