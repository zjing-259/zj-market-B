import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import org.apache.rocketmq.acl.common.*;
import org.apache.rocketmq.client.producer.*;
import org.apache.rocketmq.common.message.Message;
import org.apache.rocketmq.tools.admin.DefaultMQAdminExt;
/** Replay only the archived, hash-bound original B payment event in the isolated restore network. */
public final class RecoveryReplayProbe {
 static long offset(DefaultMQAdminExt a)throws Exception {
  long total=0;for(org.apache.rocketmq.common.admin.OffsetWrapper o:a.examineConsumeStats("A_TRADE_FACTS-b06","B_TRADE_EVENTS-b06").getOffsetTable().values())total+=o.getConsumerOffset();return total;
 }
 public static void main(String[] args)throws Exception {
  Properties p=new Properties();try(java.io.Reader r=Files.newBufferedReader(Paths.get("/test/probe.properties"),StandardCharsets.UTF_8)){p.load(r);}
  byte[] body=Files.readAllBytes(Paths.get("/test/original-event.json"));StringBuilder hash=new StringBuilder();for(byte b:MessageDigest.getInstance("SHA-256").digest(body))hash.append(String.format("%02x",b&255));
  if(args.length!=1||!hash.toString().equals(args[0]))throw new IllegalArgumentException("ORIGINAL_EVENT_HASH_MISMATCH");
  DefaultMQAdminExt admin=new DefaultMQAdminExt(new AclClientRPCHook(new SessionCredentials("B06Admin",p.getProperty("mq_admin"))),4000);admin.setNamesrvAddr("namesrv:9876");admin.setVipChannelEnabled(false);admin.start();
  DefaultMQProducer producer=new DefaultMQProducer("B066_REPLAY_"+UUID.randomUUID(),new AclClientRPCHook(new SessionCredentials("B06AppB",p.getProperty("mq_b"))));producer.setNamesrvAddr("namesrv:9876");producer.setUseTLS(true);producer.setRetryTimesWhenSendFailed(0);producer.setSendMsgTimeout(5000);producer.start();
  try {
   long before=offset(admin);for(int i=0;i<2;i++)if(producer.send(new Message("B_TRADE_EVENTS-b06","PAYMENT_SUCCEEDED",body)).getSendStatus()!=SendStatus.SEND_OK)throw new IllegalStateException("SEND_NOT_OK");
   long end=System.currentTimeMillis()+60000;while(System.currentTimeMillis()<end){long after=offset(admin);if(after>=before+2){System.out.println("RECOVERY_REPLAY_PASS originalSha256="+hash+" consumedDelta="+(after-before));return;}Thread.sleep(1000);}
   throw new IllegalStateException("ORIGINAL_DUPLICATES_NOT_CONSUMED");
  }finally{producer.shutdown();admin.shutdown();}
 }
}
