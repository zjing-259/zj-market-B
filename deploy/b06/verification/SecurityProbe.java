import cn.bugstack.api.v2.*;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.databind.*;
import org.apache.dubbo.config.*;
import org.apache.dubbo.rpc.RpcContext;
import org.apache.rocketmq.acl.common.*;
import org.apache.rocketmq.client.producer.*;
import org.apache.rocketmq.client.consumer.*;
import org.apache.rocketmq.common.message.*;
import org.apache.rocketmq.tools.admin.DefaultMQAdminExt;
import org.apache.rocketmq.common.subscription.SubscriptionGroupConfig;
import java.util.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.security.*;
import javax.crypto.*;
import javax.crypto.spec.SecretKeySpec;
/** Isolated B06 transport verification. Never included in the ordinary images. */
public final class SecurityProbe {
 static Properties p=new Properties();
 static String secret(String key){return p.getProperty(key);}
 static AclClientRPCHook acl(String account){return new AclClientRPCHook(new SessionCredentials("B06"+(account.equals("admin")?"Admin":account.equals("a")?"AppA":"AppB"),secret("mq_"+account)));}
 static String hmac(String value)throws Exception{Mac m=Mac.getInstance("HmacSHA256");m.init(new SecretKeySpec(secret("rpc").getBytes("UTF-8"),"HmacSHA256"));return Base64.getEncoder().encodeToString(m.doFinal(value.getBytes("UTF-8")));}
 static void mq(String mode)throws Exception{
  if(mode.equals("pin-route") || mode.equals("bad-pin")){
   org.apache.rocketmq.remoting.netty.NettyClientConfig nc=new org.apache.rocketmq.remoting.netty.NettyClientConfig();nc.setUseTLS(true);org.apache.rocketmq.remoting.netty.NettyRemotingClient c=new org.apache.rocketmq.remoting.netty.NettyRemotingClient(nc);c.start();
   try{org.apache.rocketmq.common.protocol.header.namesrv.GetRouteInfoRequestHeader h=new org.apache.rocketmq.common.protocol.header.namesrv.GetRouteInfoRequestHeader();h.setTopic("B061_NO_TOPIC");
    org.apache.rocketmq.remoting.protocol.RemotingCommand response=c.invokeSync("unpinned-namesrv:9876",org.apache.rocketmq.remoting.protocol.RemotingCommand.createRequestCommand(105,h),4000);
    if(response.getCode()!=17)throw new IllegalStateException("Expected empty NameServer route");
   }finally{c.shutdown();}return;
  }
  if((mode.equals("init") || mode.equals("deploy-init"))){
   DefaultMQAdminExt a=new DefaultMQAdminExt(acl("admin"));a.setNamesrvAddr("namesrv:9876");a.setVipChannelEnabled(false);a.start();
   try{for(String t:Arrays.asList("B_PRODUCT_EVENTS-b06","B_TRADE_EVENTS-b06","A_TEAM_EVENTS-b06","A_INTEGRATION_RESULTS-b06","B06_DENIED")){if(mode.equals("deploy-init") && t.equals("B06_DENIED"))continue;org.apache.rocketmq.common.TopicConfig c=new org.apache.rocketmq.common.TopicConfig(t,2,2,6);a.createAndUpdateTopicConfig("broker:10911",c);}
    for(String g:Arrays.asList("A_PRODUCT_SYNC-b06","A_TRADE_FACTS-b06","B_PRODUCT_SYNC_RESULTS-b06","B_INTEGRATION_RESULTS-b06","B_TEAM_EVENTS-b06")){SubscriptionGroupConfig c=new SubscriptionGroupConfig();c.setGroupName(g);a.createAndUpdateSubscriptionGroupConfig("broker:10911",c);}
   }finally{a.shutdown();}return;
  }
  String who=mode.equals("roundtrip")?"a":"b";
  DefaultMQProducer a=new DefaultMQProducer("B06_SECURITY_"+UUID.randomUUID(),mode.equals("bad-secret")?new AclClientRPCHook(new SessionCredentials("B06AppB","intentionally-invalid")):acl(who));
  a.setNamesrvAddr("namesrv:9876");a.setUseTLS(!mode.equals("plaintext"));a.setRetryTimesWhenSendFailed(0);a.setSendMsgTimeout(3000);
  a.start();try{
   String topic=mode.equals("denied-topic")?"B06_DENIED":mode.equals("roundtrip")?"A_TEAM_EVENTS-b06":"B_PRODUCT_EVENTS-b06";
   String body="b061-transport-only-"+UUID.randomUUID();Message message=new Message(topic,"B061_SECURITY_PROBE",body.getBytes("UTF-8"));
   SendResult sent=a.send(message);if(sent.getSendStatus()!=SendStatus.SEND_OK)throw new IllegalStateException("Send not acknowledged");
   if(mode.equals("roundtrip")){
    DefaultMQPullConsumer b=new DefaultMQPullConsumer("B_TEAM_EVENTS-b06",acl("b"));b.setNamesrvAddr("namesrv:9876");b.setUseTLS(true);b.start();
    try{MessageQueue q=new MessageQueue(topic,sent.getMessageQueue().getBrokerName(),sent.getMessageQueue().getQueueId());
     PullResult got=b.pull(q,"*",sent.getQueueOffset(),1);if(got.getPullStatus()!=PullStatus.FOUND || !body.equals(new String(got.getMsgFoundList().get(0).getBody(),"UTF-8")))throw new IllegalStateException("Roundtrip mismatch");
    }finally{b.shutdown();}
   }
  }finally{a.shutdown();}
 }
 static void rpc(String mode)throws Exception{
  if(mode.equals("plaintext")){
   try(java.net.Socket socket=new java.net.Socket("marketing-a",50051)){
    socket.setSoTimeout(3000);socket.getOutputStream().write("PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n".getBytes("US-ASCII"));socket.getOutputStream().flush();
    int b;try{b=socket.getInputStream().read();}catch(java.net.SocketException reset){throw new java.io.IOException("TLS server rejected plaintext preface",reset);}
    if(b==-1)throw new java.io.IOException("TLS server rejected plaintext preface");
    throw new AssertionError("Server answered plaintext HTTP2 preface");
   }
  }
  ApplicationConfig app=new ApplicationConfig("b061-security-"+mode);
  ReferenceConfig<TeamService> r=new ReferenceConfig<>();r.setApplication(app);r.setRegistry(new RegistryConfig("N/A"));r.setInterface(TeamService.class);r.setGroup("gbm-b06");r.setVersion("2.0.0");r.setTimeout(4000);r.setRetries(0);r.setCheck(false);
  r.setUrl("tri://marketing-a:50051?ssl-enabled="+(!mode.equals("plaintext")));
  SslConfig ssl=new SslConfig();ssl.setClientTrustCertCollectionPath("/run/secrets/rpc-server-ca.pem");
  if(!mode.equals("no-client")){ssl.setClientKeyCertChainPath(mode.equals("bad-client")?"/test/untrusted.pem":"/run/secrets/rpc-client.pem");ssl.setClientPrivateKeyPath(mode.equals("bad-client")?"/test/untrusted-key.pem":"/run/secrets/rpc-client-key.pem");}
  r.getApplicationModel().getApplicationConfigManager().setSsl(ssl);
  try{TeamService service=r.get();TeamQueryRequest q=new TeamQueryRequest();q.setSource("b06");q.setChannel("web");q.setTeamId("");
   String requestId=UUID.randomUUID().toString(),timestamp=Long.toString(System.currentTimeMillis());byte[] bytes=new byte[24];new SecureRandom().nextBytes(bytes);String nonce=Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
   ObjectMapper json=new ObjectMapper().configure(MapperFeature.SORT_PROPERTIES_ALPHABETICALLY,true).configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS,true).setSerializationInclusion(JsonInclude.Include.ALWAYS);
   byte[] hash=MessageDigest.getInstance("SHA-256").digest(json.writeValueAsBytes(q));StringBuilder hex=new StringBuilder();for(byte b:hash)hex.append(String.format("%02x",b));
   String text=String.join("\n","zj-market-b06","b06-rpc-1",timestamp,nonce,requestId,TeamService.class.getName(),"query","2.0.0","gbm-b06",hex.toString());
   Map<String,String> fields=new LinkedHashMap<>();fields.put("clientId","zj-market-b06");fields.put("keyId","b06-rpc-1");fields.put("timestamp",timestamp);fields.put("nonce",nonce);fields.put("requestId",requestId);fields.put("signature",mode.equals("bad-hmac")?"invalid":hmac(text));
   for(Map.Entry<String,String> f:fields.entrySet())RpcContext.getClientAttachment().setAttachment(f.getKey(),f.getValue());
   RpcResult<Team> result=service.query(q);
   String wanted=mode.equals("bad-hmac")?"AUTH_INVALID":"0002";
   if(!wanted.equals(result.getCode()))throw new IllegalStateException("Unexpected RPC result: "+result.getCode());
  }finally{r.destroy();app.getScopeModel().destroy();}
 }
 public static void main(String[] args)throws Exception{
  // Input is a private .properties fixture, never logged.
  try(java.io.Reader reader=Files.newBufferedReader(Paths.get("/test/probe.properties"),StandardCharsets.UTF_8)){p.load(reader);}
  if(args[1].equals("plaintext"))System.setProperty("tls.enable","false");
  boolean negative=args[1].equals("bad-pin")||args[1].equals("bad-secret")||args[1].equals("denied-topic")||args[1].equals("plaintext")||args[1].equals("bad-client")||args[1].equals("no-client")||args[1].equals("bad-ca");
  try{if(args[0].equals("mq"))mq(args[1]);else rpc(args[1]);if(negative)throw new AssertionError("Expected rejection but operation succeeded");System.out.println("PROBE_PASS "+args[0]+" "+args[1]);}
  catch(Exception e){if(!negative)throw e;String detail=e.toString();for(Throwable c=e.getCause();c!=null;c=c.getCause())detail+=" "+c;
   boolean specific=detail.matches("(?s).*(TLS|tls|SSL|ssl|handshake|Handshake|certificate|Certificate|signature|Signature|No right|permission|connect|Connect|timeout|Timeout|Remoting).*" );
   if(args[1].equals("bad-secret"))specific=detail.toLowerCase().contains("signature");
   if(args[1].equals("denied-topic"))specific=detail.toLowerCase().contains("no right")||detail.toLowerCase().contains("permission");
   if(!specific)throw e;
   for(Object value:p.values())detail=detail.replace(String.valueOf(value),"[REDACTED]");
   System.out.println("PROBE_REJECTED "+args[0]+" "+args[1]+" "+e.getClass().getSimpleName()+" "+detail);}
 }
}
