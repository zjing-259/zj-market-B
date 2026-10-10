package cn.zj.zjmarket.infrastructure.adapter.repository;
import cn.zj.zjmarket.domain.payment.adapter.repository.IFulfillmentView;
import cn.zj.zjmarket.domain.payment.service.impl.PaymentService;
import org.springframework.jdbc.core.JdbcTemplate;
import javax.sql.DataSource;
import java.util.Map;
/** Owner-scoped read remains available independently of checkout and MQ recovery. */
public final class FulfillmentView implements IFulfillmentView {
 private final JdbcTemplate db;public FulfillmentView(DataSource ds){db=new JdbcTemplate(ds);}
 public Map<String,Object> summary(String user,String order){var rows=db.queryForList("SELECT f.status,f.confirmed_at_ms,f.payment_id,f.team_id FROM b_fulfillment f JOIN b_market_order o ON o.order_id=f.order_id WHERE f.order_id=? AND o.user_id=?",order,user);if(rows.isEmpty())return null;var row=rows.getFirst();return Map.of("status",row.get("status"),"confirmedAt",PaymentService.time(((Number)row.get("confirmed_at_ms")).longValue()),"paymentId",row.get("payment_id"),"teamId",row.get("team_id"));}
}
