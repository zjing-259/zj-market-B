package cn.zj.zjmarket.verification;

import cn.zj.zjmarket.domain.payment.model.valobj.ChannelNotice;
import cn.zj.zjmarket.infrastructure.adapter.port.payment.SimulatedChannel;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.*;
import org.springframework.transaction.support.TransactionTemplate;
import javax.sql.DataSource;
import java.lang.reflect.*;
import java.sql.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import static cn.zj.zjmarket.verification.ProductCommands.check;

/** Real isolated MySQL row-lock waits; proxy observes SQL entry, never supplies fake time or results. */
final class NotificationLeaseRegression {
 private static long now(JdbcTemplate db){return db.queryForObject("SELECT CAST(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3))*1000 AS SIGNED)",Long.class);}
 private static SimulatedChannel channel(DataSource source){return new SimulatedChannel(source,new TransactionTemplate(new DataSourceTransactionManager(source)));}
 private static Map<String,Object> state(JdbcTemplate db,String id){return db.queryForMap("SELECT state,lease_token,lease_until_ms,next_attempt_ms,failure_count,fact_hash FROM b_sim_notification WHERE notification_id=?",id);}
 private static void write(SimulatedChannel c,ChannelNotice n,String action){if(action.equals("retry"))c.retry(n);else c.acknowledge(n,action.equals("review"));}
 private static DataSource observeSql(DataSource source,CountDownLatch entered){return new DelegatingDataSource(source){
  @Override public Connection getConnection() throws SQLException {
   var connection=super.getConnection();
   return (Connection)Proxy.newProxyInstance(getClass().getClassLoader(),new Class<?>[]{Connection.class},(proxy,method,args)->{
    try{var result=method.invoke(connection,args);
     if(method.getName().equals("prepareStatement")&&args[0] instanceof String sql&&sql.contains("b_sim_notification")){
      var statement=(PreparedStatement)result;
      return Proxy.newProxyInstance(getClass().getClassLoader(),new Class<?>[]{PreparedStatement.class},(p,m,a)->{
       if(m.getName().startsWith("execute"))entered.countDown();
       try{return m.invoke(statement,a);}catch(InvocationTargetException e){throw e.getCause();}
      });
     }return result;
    }catch(InvocationTargetException e){throw e.getCause();}
   });
  }
 };}
 static void run(DataSource source,String payment,String attempt,Path work)throws Exception {
  var db=new JdbcTemplate(source);var channel=channel(source);
  String id=db.queryForObject("SELECT notification_id FROM b_sim_notification WHERE payment_id=? AND attempt_id=?",String.class,payment,attempt);
  var fact=channel.fact(payment,attempt).channel();String body=new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(fact);
  String hash=db.queryForObject("SELECT fact_hash FROM b_sim_notification WHERE notification_id=?",String.class,id);
  check(state(db,id).get("state").equals("READY"),"owned new notification initially ready");
  var checks=new ArrayList<String>();
  try{
   for(String action:List.of("ack","review","retry")){
    String token=UUID.randomUUID().toString();long until=now(db)+3000;
    db.update("UPDATE b_sim_notification SET state='LEASED',lease_token=?,lease_until_ms=?,next_attempt_ms=?,failure_count=1 WHERE notification_id=?",token,until,until,id);
    var notice=new ChannelNotice(id,payment,attempt,body,hash,token,fact,1);var before=state(db,id);
    var entered=new CountDownLatch(1);var watched=channel(observeSql(source,entered));
    // Connection closes before executor: even a failing assertion releases the blocker first.
    try(var pool=Executors.newVirtualThreadPerTaskExecutor();var blocker=source.getConnection()){
     blocker.setAutoCommit(false);
     try(var lock=blocker.prepareStatement("SELECT notification_id FROM b_sim_notification WHERE notification_id=? FOR UPDATE")){lock.setString(1,id);lock.executeQuery().close();}
     var pending=pool.submit(()->write(watched,notice,action));
     check(entered.await(2,TimeUnit.SECONDS),"notification SQL entered before expiry: "+action);
     check(now(db)<until,"worker reaches notification SQL while lease valid: "+action);
     try{pending.get(150,TimeUnit.MILLISECONDS);throw new IllegalStateException("check: real notification lock did not block "+action);}catch(TimeoutException expected){/* Actual JDBC statement is blocked by our uncommitted row lock. */}
     long bounded=System.nanoTime()+TimeUnit.SECONDS.toNanos(8);
     while(now(db)<=until){check(System.nanoTime()<bounded,"bounded database expiry wait");Thread.sleep(50);}
     check(!pending.isDone(),"notification operation still blocked after expiry: "+action);
     blocker.commit();pending.get(5,TimeUnit.SECONDS);
    }
    check(before.equals(state(db,id)),"expired lock-wait write changes no notification state: "+action);
    checks.add("real-row-lock-valid-to-expired-"+action+"=PASSED");
   }
   for(String action:List.of("ack","review","retry")){
    String old=UUID.randomUUID().toString();
    // Only this probe's row is prioritized; no unrelated notice is claimed or cleared.
    db.update("UPDATE b_sim_notification SET state='LEASED',lease_token=?,lease_until_ms=0,next_attempt_ms=-1 WHERE notification_id=?",old,id);
    var stale=new ChannelNotice(id,payment,attempt,body,hash,old,fact,1);
    var claimed=channel.notices(1);check(claimed.size()==1&&claimed.getFirst().id().equals(id),"owned expired notification reclaimed");
    var current=claimed.getFirst();check(!current.token().equals(old),"replacement has new token");var before=state(db,id);
    write(channel,stale,action);check(before.equals(state(db,id)),"old token cannot change replacement: "+action);
    if(action.equals("retry")){
     channel.retry(current);var retried=state(db,id);check(retried.get("state").equals("READY")&&retried.get("lease_token")==null&&retried.get("lease_until_ms")==null&&((Number)retried.get("next_attempt_ms")).longValue()>now(db),"current valid retry remains effective");
    }else{
     channel.acknowledge(current,action.equals("review"));check(state(db,id).get("state").equals(action.equals("review")?"REVIEW_REQUIRED":"DONE"),"current valid ACK remains effective");
     var terminal=state(db,id);channel.retry(current);channel.acknowledge(current,!action.equals("review"));check(terminal.equals(state(db,id)),"terminal notification cannot be changed by duplicate calls");
    }
    checks.add("replaced-token-"+action+"/valid-current-writer=PASSED");
   }
  }finally{
   // Restore only this originally unhandled notification, leaving the channel/money facts intact.
   db.update("UPDATE b_sim_notification SET state='READY',lease_token=NULL,lease_until_ms=NULL,next_attempt_ms=0 WHERE notification_id=?",id);
  }
  checks.addFirst("status=PASSED");Files.write(work.resolve("notification-lease.txt"),checks);
 }
}
