import java.util.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import org.apache.rocketmq.acl.common.*;
import org.apache.rocketmq.tools.admin.DefaultMQAdminExt;
import org.apache.rocketmq.client.producer.*;
import org.apache.rocketmq.common.message.Message;
/** Read-only broker route/stats controls; negative publish must be rejected on an EXISTING A topic. */
public final class FaultTransportProbe {
 public static void main(String[] args)throws Exception {
  Properties p=new Properties();try(java.io.Reader r=Files.newBufferedReader(Paths.get("/test/probe.properties"),StandardCharsets.UTF_8)){p.load(r);}
  String mode=args[0];boolean negative=mode.equals("bad-secret")||mode.equals("bad-ca")||mode.equals("denied-topic");
  try {
   if(mode.equals("denied-topic")) {
    DefaultMQProducer producer=new DefaultMQProducer("B065_DENIED_"+UUID.randomUUID(),new AclClientRPCHook(new SessionCredentials("B06AppB",p.getProperty("mq_b"))));
    producer.setNamesrvAddr("namesrv:9876");producer.setUseTLS(true);producer.setRetryTimesWhenSendFailed(0);producer.setSendMsgTimeout(3000);producer.start();
    try{producer.send(new Message("A_TEAM_EVENTS-b06","B065_MUST_BE_DENIED","no-business-fact".getBytes("UTF-8")));}finally{producer.shutdown();}
   }else {
    DefaultMQAdminExt admin=new DefaultMQAdminExt(new AclClientRPCHook(new SessionCredentials("B06Admin",mode.equals("bad-secret")?"intentionally-invalid":p.getProperty("mq_admin"))),4000);
    admin.setNamesrvAddr("namesrv:9876");admin.setVipChannelEnabled(false);admin.start();
    try{org.apache.rocketmq.common.admin.TopicStatsTable stats=admin.examineTopicStats("B_TRADE_EVENTS-b06");
     if(stats.getOffsetTable().isEmpty())throw new IllegalStateException("EMPTY_TOPIC_STATS");
     long total=0;for(org.apache.rocketmq.common.admin.TopicOffset offset:stats.getOffsetTable().values())total+=offset.getMaxOffset();
     System.out.println("BROKER_STATS queues="+stats.getOffsetTable().size()+" maxOffsetSum="+total);
    }finally{admin.shutdown();}
   }
   if(negative)throw new AssertionError("NEGATIVE_OPERATION_SUCCEEDED");System.out.println("FAULT_TRANSPORT_PASS "+mode);
  }catch(Exception e){
   if(!negative)throw e;String text=e.toString();for(Throwable c=e.getCause();c!=null;c=c.getCause())text+=" "+c;
   String lower=text.toLowerCase(Locale.ROOT);
   boolean specific=mode.equals("bad-ca")?(lower.contains("ssl")||lower.contains("connect")||lower.contains("handshake")):(lower.contains("signature")||lower.contains("permission")||lower.contains("no right")||lower.contains("access"));
   if(!specific)throw e;
   for(Object value:p.values())text=text.replace(String.valueOf(value),"[REDACTED]");
   System.out.println("FAULT_TRANSPORT_REJECTED "+mode+" "+e.getClass().getSimpleName());
  }
 }
}
