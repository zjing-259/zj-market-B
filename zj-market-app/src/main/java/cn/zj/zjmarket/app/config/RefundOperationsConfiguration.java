package cn.zj.zjmarket.app.config;
import cn.zj.zjmarket.infrastructure.adapter.repository.*;
import org.springframework.context.annotation.*;
import org.springframework.boot.autoconfigure.condition.*;
import org.springframework.beans.factory.ObjectProvider;
import javax.sql.DataSource;
@Configuration(proxyBeanMethods=false) @ConditionalOnProperty(name="b.order.enabled",havingValue="true")
public class RefundOperationsConfiguration {
 @Bean RefundOperationsRepository refundOperations(DataSource ds,ObjectProvider<RefundRepository> refunds){var db=new org.springframework.jdbc.core.JdbcTemplate(ds);db.queryForList("SELECT release_status FROM b_refund LIMIT 0");db.queryForList("SELECT operation_id FROM b_refund_operation LIMIT 0");return new RefundOperationsRepository(ds,refunds.getIfAvailable());}
}
