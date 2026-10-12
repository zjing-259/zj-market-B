import java.util.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.*;
import org.springframework.transaction.support.TransactionTemplate;
import cn.zj.zjmarket.domain.refund.model.Refund.*;
import cn.zj.zjmarket.domain.refund.adapter.port.IRefundChannel;
import cn.zj.zjmarket.domain.refund.service.RefundService;
import cn.zj.zjmarket.infrastructure.adapter.repository.*;
import cn.zj.zjmarket.infrastructure.adapter.port.refund.SimulatedRefundChannel;
/** Explicit verification only. No ordinary web interface; all facts created by original domain/channel methods. */
public final class RefundFaultProbe {
 static void require(boolean v,String code){if(!v)throw new IllegalStateException(code);}
 public static void main(String[] args)throws Exception {
  Properties config=new Properties(),scope=new Properties();
  try(var r=Files.newBufferedReader(Path.of("/run/secrets/b.properties"),StandardCharsets.UTF_8)){config.load(r);}
  try(var r=Files.newBufferedReader(Path.of("/test/refunds.properties"),StandardCharsets.UTF_8)){scope.load(r);}
  String blocked=scope.getProperty("blocked"),healthy=scope.getProperty("healthy");
  for(String key:List.of("blocked","healthy","blockedOrder","healthyOrder"))require(scope.getProperty(key,"").matches("[A-Za-z0-9_-]{1,64}"),"INVALID_SCOPE");
  require(!blocked.equals(healthy),"SCOPE_MUST_DIFFER");
  var ds=new DriverManagerDataSource(config.getProperty("b.infrastructure.database.url"),"b_runtime",config.getProperty("b.infrastructure.database.password"));
  var db=new JdbcTemplate(ds);var tx=new TransactionTemplate(new DataSourceTransactionManager(ds));tx.setIsolationLevel(org.springframework.transaction.TransactionDefinition.ISOLATION_READ_COMMITTED);tx.setTimeout(15);
  var settings=Settings.defaults();var repo=new RefundRepository(ds,tx,settings,"b06","web");repo.validateSchema();repo.enableOutbox(new RefundOutbox(db,"zj-market-b06","b06","web"));
  var channel=new SimulatedRefundChannel(ds,tx,settings);
  for(String id:List.of(blocked,healthy)) {
   String expected=scope.getProperty(id.equals(blocked)?"blockedOrder":"healthyOrder");
   require(db.queryForObject("SELECT COUNT(*) FROM b_refund WHERE refund_id=? AND order_id=? AND eligibility_status='ELIGIBLE' AND eligibility_basis='TEAM_FAILED_ACCEPTED'",Long.class,id,expected)==1,"NOT_THIS_BATCH_ELIGIBLE_REFUND");
  }
  String action=args[0];require(Set.of("drop-response","isolate").contains(action),"UNKNOWN_ACTION");
  IRefundChannel fault=new IRefundChannel(){
   public Fact query(Request r){if(action.equals("isolate")&&r.refundId().equals(blocked))throw new IllegalStateException("VERIFICATION_QUERY_UNKNOWN");return channel.query(r);}
   public Fact execute(Request r){Fact f=channel.execute(r);if(action.equals("drop-response")&&r.refundId().equals(blocked))throw new IllegalStateException("VERIFICATION_RESPONSE_LOST_AFTER_CHANNEL_COMMIT");return f;}
   public List<Notice> notices(int size){return List.of();}
   public boolean renew(Notice n){return channel.renew(n);}public void acknowledge(Notice n,boolean review){channel.acknowledge(n,review);}public void retry(Notice n){channel.retry(n);}
  };
  try(var service=new RefundService(repo,fault,settings)){
   if(action.equals("drop-response")){repo.admit(blocked);service.recover(blocked);}
   else{repo.admit(healthy);var due=repo.due(20);require(due.contains(blocked)&&due.contains(healthy),"BOTH_TASKS_MUST_BE_DUE");require(due.stream().allMatch(id->id.equals(blocked)||id.equals(healthy)),"UNSCOPED_DUE_TASK");service.tick(20,false);}
  }
  require(db.queryForObject("SELECT funds_status FROM b_refund WHERE refund_id=?",String.class,blocked).equals("UNKNOWN"),"MARKETPLACE_MUST_REMAIN_UNKNOWN");
  require(db.queryForObject("SELECT COUNT(*) FROM b_sim_refund_attempt WHERE refund_id=? AND state='SUCCEEDED'",Long.class,blocked)==1,"CHANNEL_COMMITTED_ONCE");
  require(db.queryForObject("SELECT COUNT(*) FROM b_refund_attempt WHERE refund_id=?",Long.class,blocked)==1,"UNKNOWN_MUST_KEEP_ORIGINAL_ATTEMPT");
  require(db.queryForObject("SELECT COUNT(*) FROM b_inventory_ledger WHERE order_id=? AND kind='RELEASE'",Long.class,scope.getProperty("blockedOrder"))==0,"UNKNOWN_MUST_NOT_RELEASE");
  if(action.equals("isolate"))require(db.queryForObject("SELECT funds_status FROM b_refund WHERE refund_id=?",String.class,healthy).equals("SUCCEEDED"),"OTHER_TASK_MUST_PROGRESS");
  System.out.println("REFUND_FAULT_PASS "+action);
 }
}
