package cn.zj.zjmarket.verification;
import cn.bugstack.api.v2.*;
import cn.zj.zjmarket.infrastructure.config.RpcSettings;
import cn.zj.zjmarket.infrastructure.product.DubboMarketingTrial;
import cn.zj.zjmarket.infrastructure.integration.rpc.RpcClientFactory;
import org.springframework.context.ApplicationContext;
import com.fasterxml.jackson.databind.JsonNode;
import javax.net.ssl.*;
import java.security.*;
import java.security.cert.*;
import java.security.spec.PKCS8EncodedKeySpec;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
/** Controlled envelope inputs and a separate TLS socket stalled on actual SDK traffic, never actual A. */
final class TrialRpcFaults {
 static void verify(ApplicationContext ctx,ProductCommands.Client http,String jwt,JsonNode f,TrialCommands.Bridge bridge)throws Exception{
  for(String fault:List.of("REQUEST_ID","FLAGS","NULL")){
   bridge.target=(u,p,id)->{var q=new TrialResponse();q.setAvailable(fault.equals("FLAGS")?null:true);q.setVisible(true);q.setEligible(true);q.setQuotedAt(TrialCommands.good(p).quotedAt());return DubboMarketingTrial.readResponse(new RpcResult<>("0000","ok",fault.equals("NULL")?null:q,fault.equals("REQUEST_ID")?"wrong-id":id),id);};
   SyncCommands.check(http.call("POST",TrialCommands.path(f,"public"),Map.of(),jwt,502).path("code").asText().equals("UPSTREAM_RESPONSE_INVALID"),"controlled typed RPC envelope "+fault);
  }
  bridge.target=null;var real=ctx.getBean(RpcSettings.class);
  String pem=Files.readString(Path.of(real.getClientPrivateKey())).replace("-----BEGIN PRIVATE KEY-----","").replace("-----END PRIVATE KEY-----","").replaceAll("\\s","");
  var key=KeyFactory.getInstance("RSA").generatePrivate(new PKCS8EncodedKeySpec(Base64.getDecoder().decode(pem)));
  java.security.cert.Certificate cert;try(var input=Files.newInputStream(Path.of(real.getClientCertificate()))){cert=CertificateFactory.getInstance("X.509").generateCertificate(input);}
  var store=KeyStore.getInstance("PKCS12");store.load(null,null);store.setKeyEntry("fixture",key,"fixture-only".toCharArray(),new java.security.cert.Certificate[]{cert});
  var km=KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm());km.init(store,"fixture-only".toCharArray());var ssl=SSLContext.getInstance("TLS");ssl.init(km.getKeyManagers(),null,null);
  try(var listener=(SSLServerSocket)ssl.getServerSocketFactory().createServerSocket(0,1);var executor=Executors.newSingleThreadExecutor()){
   var parameters=listener.getSSLParameters();parameters.setApplicationProtocols(new String[]{"h2"});listener.setSSLParameters(parameters);listener.setSoTimeout(10000);var received=new CountDownLatch(1);var release=new CountDownLatch(1);var worker=executor.submit(()->{try(var socket=(SSLSocket)listener.accept()){socket.setSoTimeout(10000);socket.startHandshake();if(socket.getInputStream().read()!=-1){received.countDown();release.await(10,TimeUnit.SECONDS);}}catch(Exception failure){throw new RuntimeException(failure);}});
   var slow=TrialCommands.copy(real);slow.setUrl("tri://127.0.0.1:"+listener.getLocalPort()+"?ssl-enabled=true");slow.setTimeoutMillis(700);
   try(var adapter=new DubboMarketingTrial(slow,new RpcClientFactory(slow))){bridge.target=adapter;SyncCommands.check(http.call("POST",TrialCommands.path(f,"public"),Map.of(),jwt,504).path("code").asText().equals("UPSTREAM_TIMEOUT"),"actual SDK TLS timeout maps504");SyncCommands.check(received.await(5,TimeUnit.SECONDS),"controlled TLS server received actual SDK traffic");}
   finally{bridge.target=null;release.countDown();}
   worker.get(10,TimeUnit.SECONDS);
  }
  System.out.println("B controlled envelope + actual SDK stalled TLS timeout: PASSED");
 }
}
