package cn.zj.zjmarket.test.order;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import cn.zj.zjmarket.domain.order.adapter.repository.IOrderRepository;
import cn.zj.zjmarket.domain.order.adapter.port.IPurchaseQuotePort;
import cn.zj.zjmarket.domain.order.model.entity.*;
import cn.zj.zjmarket.domain.order.model.valobj.*;
import cn.zj.zjmarket.domain.order.service.impl.OrderService;
import cn.zj.zjmarket.domain.product.model.valobj.TrialOffer;
import cn.zj.zjmarket.types.exception.OrderFailure;
class OrderServiceTest {
 static PurchaseConditions conditions(){return new PurchaseConditions("sku","OPEN",null,new TrialOffer("1","sku","1","10.00","1.00","9.00","CNY",2));}
 @Test void rejectsInexactAmountsVersionsAndWrongTeamShape(){
  assertThrows(OrderFailure.class,()->new PurchaseConditions("sku","OPEN","team",conditions().expectedOffer()));
  assertThrows(OrderFailure.class,()->new PurchaseConditions("sku","JOIN",null,conditions().expectedOffer()));
  assertThrows(OrderFailure.class,()->new PurchaseConditions("sku","OPEN",null,new TrialOffer("9223372036854775808","sku","1","10.00","1.00","9.00","CNY",2)));
  assertThrows(OrderFailure.class,()->new PurchaseConditions("sku","OPEN",null,new TrialOffer("1","sku","1","10.00","1.00","8.99","CNY",2)));
  assertNotNull(conditions());
 }
 @Test void replayNeverNeedsLiveQuoteOrCurrentProduct(){
  var repo=mock(IOrderRepository.class);var port=mock(IPurchaseQuotePort.class);var c=new PurchaseConfirmation("confirm","user","s","c",conditions(),"name",null,1,2,1L);
  var order=new MarketOrder("order","intent",OrderService.hash("user","s","c","intent","confirm"),c,"PROCESSING",1,1,300001,false,"NEVER_OPENED");
  when(repo.byIntent("user","s","c","intent")).thenReturn(order);var service=new OrderService(repo,port,"s","c");
  assertTrue(service.create("user","intent","confirm","request").replay());verifyNoInteractions(port);
  assertEquals("IDEMPOTENCY_CONFLICT",assertThrows(OrderFailure.class,()->service.create("user","intent","different","request")).code());
 }
 @Test void foreignConfirmationNeverCallsMarketing(){
  var repo=mock(IOrderRepository.class);var port=mock(IPurchaseQuotePort.class);
  when(repo.confirmation("confirm",false)).thenReturn(new PurchaseConfirmation("confirm","other","s","c",conditions(),"name",null,1,300001,null));
  var service=new OrderService(repo,port,"s","c");assertEquals(404,assertThrows(OrderFailure.class,()->service.create("user","intent","confirm","request")).status());verifyNoInteractions(port);
 }
 @Test void expiredConfirmationCannotReachNetwork(){
  var repo=mock(IOrderRepository.class);var port=mock(IPurchaseQuotePort.class);
  when(repo.confirmation("confirm",false)).thenReturn(new PurchaseConfirmation("confirm","user","s","c",conditions(),"name",null,1,300001,null));when(repo.now()).thenReturn(300001L);
  assertEquals("CONFIRMATION_EXPIRED",assertThrows(OrderFailure.class,()->new OrderService(repo,port,"s","c").create("user","intent","confirm","request")).code());verifyNoInteractions(port);
 }

 private static IOrderRepository freshRepository(){
  var repo=mock(IOrderRepository.class);
  when(repo.transaction(any())).thenAnswer(i->((java.util.function.Supplier<?>)i.getArgument(0)).get());
  when(repo.now()).thenReturn(1000L);
  when(repo.lockSaleProduct(any())).thenReturn(new cn.zj.zjmarket.domain.product.model.entity.Product("sku",new cn.zj.zjmarket.domain.product.model.valobj.ProductFields("name","",null,"10.00","CNY",cn.zj.zjmarket.domain.product.model.valobj.SaleStatus.ON_SALE),1,1,1));
  when(repo.lockInventory("sku")).thenReturn(new cn.zj.zjmarket.domain.inventory.model.entity.InventoryAccount("sku",1,0,0,1,1));
  return repo;
 }
 private static MarketOrder create(OrderService service,IOrderRepository repo){
  var c=service.confirm("user",conditions(),"quote");
  assertEquals(300000,c.expiresAt()-c.issuedAt(),"D9 confirmation TTL must be independent of D6");
  when(repo.confirmation(c.confirmationId(),false)).thenReturn(c);
  when(repo.confirmation(c.confirmationId(),true)).thenReturn(c);
  return service.create("user","intent",c.confirmationId(),"create").order();
 }
 @Test void configuredWaitIsPersistedWithoutChangingConfirmationTtl(){
  var repo=freshRepository();var service=new OrderService(repo,mock(IPurchaseQuotePort.class),"s","c",60000);
  var order=create(service,repo);assertEquals(60000,order.reserveWaitDeadline()-order.createdAt());
  verify(repo).create(eq(order),any(),any());
 }
 @Test void defaultIsFiveMinutesAndChangedConfigurationCannotRewriteReplay(){
  var repo=freshRepository();var port=mock(IPurchaseQuotePort.class);var order=create(new OrderService(repo,port,"s","c"),repo);
  assertEquals(300000,order.reserveWaitDeadline()-order.createdAt());
  when(repo.byIntent("user","s","c","intent")).thenReturn(order);clearInvocations(port);
  var replay=new OrderService(repo,port,"s","c",1).create("user","intent",order.confirmation().confirmationId(),"retry");
  assertTrue(replay.replay());assertEquals(order.reserveWaitDeadline(),replay.order().reserveWaitDeadline());verifyNoInteractions(port);
 }
 @Test void invalidWaitIsRejectedAndDeadlineOverflowNeverCreatesOrder(){
  for(long invalid:new long[]{0,-1,Long.MIN_VALUE})assertThrows(IllegalArgumentException.class,()->new OrderService(mock(IOrderRepository.class),mock(IPurchaseQuotePort.class),"s","c",invalid));
  var repo=freshRepository();var service=new OrderService(repo,mock(IPurchaseQuotePort.class),"s","c",Long.MAX_VALUE);
  assertThrows(ArithmeticException.class,()->create(service,repo));verify(repo,never()).create(any(),any(),any());
 }
}
