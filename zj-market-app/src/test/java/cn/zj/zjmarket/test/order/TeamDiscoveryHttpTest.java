package cn.zj.zjmarket.test.order;

import cn.zj.zjmarket.app.config.IdentityWebConfiguration;
import cn.zj.zjmarket.domain.identity.model.valobj.*;
import cn.zj.zjmarket.domain.identity.service.IIdentityService;
import cn.zj.zjmarket.domain.order.adapter.port.ITeamDiscoveryPort;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
import cn.zj.zjmarket.domain.order.model.valobj.*;
import cn.zj.zjmarket.domain.order.service.*;
import cn.zj.zjmarket.domain.order.service.impl.TeamDiscoveryService;
import cn.zj.zjmarket.domain.product.model.entity.Product;
import cn.zj.zjmarket.domain.product.model.valobj.*;
import cn.zj.zjmarket.domain.product.service.*;
import cn.zj.zjmarket.domain.inventory.model.entity.InventoryAccount;
import cn.zj.zjmarket.domain.inventory.service.IInventoryService;
import cn.zj.zjmarket.infrastructure.adapter.port.order.DubboTeamDiscoveryPort;
import cn.zj.zjmarket.infrastructure.config.properties.*;
import cn.zj.zjmarket.infrastructure.gateway.rpc.RpcClientFactory;
import cn.zj.zjmarket.trigger.http.*;
import cn.zj.zjmarket.types.exception.AuthFailure;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.SpringBootConfiguration;
import org.springframework.boot.autoconfigure.EnableAutoConfiguration;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.context.annotation.*;
import java.net.*;
import java.net.http.*;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
@SpringBootTest(classes=TeamDiscoveryHttpTest.App.class,webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT,properties={"b.identity.enabled=true","b.team-discovery.enabled=true","spring.autoconfigure.exclude=org.springframework.boot.jdbc.autoconfigure.DataSourceAutoConfiguration,org.mybatis.spring.boot.autoconfigure.MybatisAutoConfiguration"})
class TeamDiscoveryHttpTest {
 static final String GOODS="td01-live-goods",NOW="2026-10-14T10:00:00.000Z";
 static final AtomicReference<MarketOrder> ACTIVE=new AtomicReference<>();
 @SpringBootConfiguration @EnableAutoConfiguration @Import({IdentityWebConfiguration.class,TeamDiscoveryController.class})
 static class App {
  @Bean IdentitySettings settings(){var s=new IdentitySettings();s.setEnabled(true);s.setOrigin("http://127.0.0.1");s.setSecureCookies(false);return s;}
  @Bean IIdentityService identity(){var s=mock(IIdentityService.class);when(s.authenticate("viewer")).thenReturn(new AuthenticatedPrincipal(new UserView("viewer","viewer","Viewer",Set.of("USER")),"grant"));when(s.authenticate("operator")).thenReturn(new AuthenticatedPrincipal(new UserView("viewer","operator","Operator",Set.of("OPERATOR")),"grant"));when(s.authenticate("observer")).thenReturn(new AuthenticatedPrincipal(new UserView("viewer","observer","Observer",Set.of()),"grant"));when(s.authenticate("expired")).thenThrow(new AuthFailure(401,"AUTH_INVALID"));return s;}
  @Bean IProductService products(){var s=mock(IProductService.class);var view=new ProductView(new Product(GOODS,new ProductFields("TD01","",null,"100.00","CNY",SaleStatus.ON_SALE),1,1,1),new ProductSyncProgress(GOODS,"1","event","1","CONFIRMED",null,NOW));when(s.detail(GOODS,false)).thenReturn(view);when(s.detail(GOODS,true)).thenReturn(view);return s;}
  @Bean IOrderService orders(){var s=mock(IOrderService.class);when(s.active("viewer",GOODS)).thenAnswer(x->ACTIVE.get());return s;}
  @Bean IInventoryService stock(){var s=mock(IInventoryService.class);when(s.detail(GOODS)).thenReturn(new InventoryAccount(GOODS,100,0,0,1,1));return s;}
  @Bean IMarketingTrialService trial(){var s=mock(IMarketingTrialService.class);when(s.trial(eq("viewer"),eq(GOODS),anyString())).thenReturn(new TrialResult(GOODS,"1",NOW,"AVAILABLE",new TrialOffer("714201",GOODS,"1","100.00","10.00","90.00","CNY",3)));return s;}
  @Bean(destroyMethod="close") ITeamDiscoveryPort discovery(){
   if(System.getenv("TD02_A_URL")!=null){var s=new RpcSettings();s.setEnabled(true);s.setUrl(System.getenv("TD02_A_URL"));s.setVersion("2.0.0");s.setGroup("gbm-td01");s.setClientId("td01-client");s.setKeyId("td01-key");s.setSecret(System.getenv("TD02_RPC_SECRET"));s.setSource("td01");s.setChannel("web");s.setClientCertificate(System.getenv("TD02_TLS_CERT"));s.setClientPrivateKey(System.getenv("TD02_TLS_KEY"));s.setTrustCertificate(System.getenv("TD02_TLS_CERT"));return new DubboTeamDiscoveryPort(s,new RpcClientFactory(s));}
   return new ITeamDiscoveryPort(){public void close(){}public void validateCursor(String user,String goods,String cursor){if(cursor!=null&&!cursor.equals("next"))throw new cn.zj.zjmarket.types.exception.ProductFailure(400,"VALIDATION_FAILED");}public DiscoveryPage list(String user,String goods,String activity,String version,int target,int limit,String cursor,String requestId){return new DiscoveryPage("AVAILABLE",null,goods,version,activity,NOW,List.of(new DiscoveryItem("td01-live-0000",3,2,1,1,2,"2026-10-14T12:00:00.000Z")),null,null,false);}};
  }
  @Bean ITeamDiscoveryService discoveryService(IProductService products,IOrderService orders,IInventoryService stock,IMarketingTrialService trial,ITeamDiscoveryPort port){return new TeamDiscoveryService(products,orders,stock,trial,port);}
  @Bean(destroyMethod="close") TeamDiscoveryGate gate(){return new TeamDiscoveryGate(100,4);}
 }
 @LocalServerPort int port;
 @BeforeEach void reset(){ACTIVE.set(null);}
 private HttpResponse<String> get(String suffix,String token)throws Exception{var builder=HttpRequest.newBuilder(URI.create("http://127.0.0.1:"+port+"/api/v1/products/"+GOODS+"/joinable-teams"+suffix)).timeout(Duration.ofSeconds(12)).GET();if(token!=null)builder.header("Authorization","Bearer "+token);return HttpClient.newHttpClient().send(builder.build(),HttpResponse.BodyHandlers.ofString());}
 private void warm()throws Exception {if(System.getenv("TD02_A_URL")==null)return;for(int i=0;i<3;i++){var result=get("","viewer");if(result.statusCode()==200)return;assertEquals(503,result.statusCode(),result.body());Thread.sleep(250);}fail("Real A provider stayed unavailable after bounded cold-start calls");}
 @Test @Order(1) void actualHttpAuthParamsAndNoStore()throws Exception {var no=get("",null);assertEquals(401,no.statusCode());assertTrue(no.body().contains("AUTH_REQUIRED"));assertEquals("no-store",no.headers().firstValue("Cache-Control").orElse(null));assertEquals(403,get("","observer").statusCode());assertEquals(401,get("","expired").statusCode());for(String suffix:List.of("?userId=other","?limit=0","?limit=11","?limit=3&limit=4","?cursor=bad="))assertEquals(400,get(suffix,"viewer").statusCode(),suffix);var body=HttpRequest.newBuilder(URI.create("http://127.0.0.1:"+port+"/api/v1/products/"+GOODS+"/joinable-teams")).header("Authorization","Bearer viewer").method("GET",HttpRequest.BodyPublishers.ofString("body")).build();assertEquals(400,HttpClient.newHttpClient().send(body,HttpResponse.BodyHandlers.ofString()).statusCode());}
 @Test @Order(2) void actualHttpReturnsOnlySafeSummaryAndOriginalPurchaseFirst()throws Exception {warm();var response=get("","viewer");assertEquals(200,response.statusCode(),response.body());assertEquals("no-store",response.headers().firstValue("Cache-Control").orElse(null));assertTrue(response.body().contains("\"availableSlots\":1"));assertFalse(response.body().contains("outTradeNo"));assertFalse(response.body().contains("ownReservation"));var order=mock(MarketOrder.class);when(order.orderId()).thenReturn("my-order");ACTIVE.set(order);var active=get("","operator");assertEquals(200,active.statusCode());assertTrue(active.body().contains("ACTIVE_PURCHASE"));assertTrue(active.body().contains("my-order"));assertTrue(active.body().contains("\"items\":[]"));}
 @Test @Order(3) void realAProviderPaginatesWhenConfigured()throws Exception {if(System.getenv("TD02_A_URL")==null)return;warm();var first=get("?limit=2","viewer");assertEquals(200,first.statusCode(),first.body());var json=new tools.jackson.databind.ObjectMapper().readTree(first.body());String cursor=json.path("data").path("nextCursor").asText();assertFalse(cursor.isEmpty());assertEquals(2,json.path("data").path("items").size());var next=get("?limit=2&cursor="+URLEncoder.encode(cursor,java.nio.charset.StandardCharsets.UTF_8),"viewer");assertEquals(200,next.statusCode(),next.body());assertTrue(next.body().contains("td01-live-0002"));}
 @Test @Order(4) void healthyRealAHttpP95IsBounded()throws Exception {String path=System.getenv("TD02_METRICS");if(path==null)return;warm();List<Long> times=new ArrayList<>();for(int i=0;i<20;i++){long start=System.nanoTime();assertEquals(200,get("?limit=10","viewer").statusCode());times.add((System.nanoTime()-start)/1_000_000);}Collections.sort(times);assertTrue(times.get(18)<=1000,"HTTP p95="+times.get(18));java.nio.file.Files.writeString(java.nio.file.Path.of(path),"{\"samples\":20,\"concurrency\":1,\"httpP95Millis\":"+times.get(18)+",\"httpMaxMillis\":"+times.get(19)+"}\n");}
 @Test @Order(5) void stoppedRealAProviderReturns503()throws Exception {String path=System.getenv("TD02_STOP_FILE");if(path==null)return;java.nio.file.Files.createFile(java.nio.file.Path.of(path));for(int i=0;i<12;i++){var r=get("","viewer");if(r.statusCode()==503){assertTrue(r.body().contains("DEPENDENCY_UNAVAILABLE"));return;}Thread.sleep(400);}fail("Stopped provider still returned success");}
}
