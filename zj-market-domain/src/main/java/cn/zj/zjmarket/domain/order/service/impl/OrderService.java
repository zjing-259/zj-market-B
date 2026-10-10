package cn.zj.zjmarket.domain.order.service.impl;
import cn.zj.zjmarket.domain.order.adapter.repository.IOrderRepository;
import cn.zj.zjmarket.domain.order.adapter.port.IPurchaseQuotePort;
import cn.zj.zjmarket.domain.order.model.entity.*;
import cn.zj.zjmarket.domain.order.model.valobj.*;
import cn.zj.zjmarket.domain.order.service.IOrderService;
import cn.zj.zjmarket.types.exception.OrderFailure;
import java.util.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
public final class OrderService implements IOrderService {
 private final IOrderRepository repo;private final IPurchaseQuotePort quote;private final String source,channel;private final long reserveWaitMillis;
 public OrderService(IOrderRepository repo,IPurchaseQuotePort quote,String source,String channel){this(repo,quote,source,channel,300000L);}
 public OrderService(IOrderRepository repo,IPurchaseQuotePort quote,String source,String channel,long reserveWaitMillis){if(reserveWaitMillis<=0)throw new IllegalArgumentException("Order reserve wait millis must be positive");this.reserveWaitMillis=reserveWaitMillis;if(source==null||source.isBlank()||channel==null||channel.isBlank())throw new IllegalArgumentException("Order scope required");this.repo=repo;this.quote=quote;this.source=source;this.channel=channel;}
 public PurchaseConfirmation confirm(String user,PurchaseConditions conditions,String requestId){
  PurchaseConditions.id(user);quote.verify(user,conditions,requestId);
  return repo.transaction(()->{repo.lockBuyer(user);var product=repo.lockSaleProduct(conditions);long now=repo.now();var c=new PurchaseConfirmation(UUID.randomUUID().toString(),user,source,channel,conditions,product.fields().goodsName(),product.fields().imageUrl(),now,Math.addExact(now,300000),null);repo.insertConfirmation(c);return c;});
 }
 public OrderWrite create(String user,String intent,String confirmationId,String requestId){
  PurchaseConditions.id(user);PurchaseConditions.id(intent);PurchaseConditions.id(confirmationId);
  String hash=hash(user,source,channel,intent,confirmationId);
  var prior=repo.byIntent(user,source,channel,intent);if(prior!=null)return replay(prior,hash);
  var located=requireConfirmation(user,confirmationId,false);
  // A network read is never executed while holding user/product/stock locks.
  if(located.boundAt()!=null || repo.bound(confirmationId))throw failure("CONFIRMATION_ALREADY_USED");
  if(repo.now()>=located.expiresAt())throw failure("CONFIRMATION_EXPIRED");
  quote.verify(user,located.conditions(),requestId);
  return repo.transaction(()->{
   repo.lockBuyer(user);
   // Same intent may have committed while the network call was in flight.
   var won=repo.byIntent(user,source,channel,intent);if(won!=null)return replay(won,hash);
   var product=repo.lockSaleProduct(located.conditions());
   String active=repo.lockGuard(user,product.goodsId(),repo.now());
   won=repo.byIntent(user,source,channel,intent);if(won!=null)return replay(won,hash);
   if(active!=null)throw new OrderFailure(409,"ACTIVE_PURCHASE_EXISTS",Map.of("activeOrderId",active));
   var c=requireConfirmation(user,confirmationId,true);
   var stock=repo.lockInventory(product.goodsId());long now=repo.now();
   if(c.boundAt()!=null || repo.bound(confirmationId))throw failure("CONFIRMATION_ALREADY_USED");
   if(now>=c.expiresAt())throw failure("CONFIRMATION_EXPIRED");
   cn.zj.zjmarket.domain.inventory.model.entity.InventoryAccount after;
   try{after=stock.reserve(1,now);}catch(ArithmeticException e){throw failure(stock.version()==Long.MAX_VALUE?"INVENTORY_VERSION_EXHAUSTED":"INVENTORY_QUANTITY_OVERFLOW");}
   var order=new MarketOrder(UUID.randomUUID().toString(),intent,hash,c,"PROCESSING",1,now,Math.addExact(now,reserveWaitMillis),false,"NEVER_OPENED");
   repo.create(order,stock,after);return new OrderWrite(order,false);
  });
 }
 private PurchaseConfirmation requireConfirmation(String user,String id,boolean lock){var c=repo.confirmation(id,lock);if(c==null||!c.userId().equals(user)||!c.source().equals(source)||!c.channel().equals(channel))throw new OrderFailure(404,"CONFIRMATION_NOT_FOUND");return c;}
 private static OrderWrite replay(MarketOrder o,String hash){if(!o.requestHash().equals(hash))throw failure("IDEMPOTENCY_CONFLICT");return new OrderWrite(o,true);}
 public MarketOrder detail(String user,String id){PurchaseConditions.id(user);PurchaseConditions.id(id);var o=repo.byId(user,id);if(o==null)throw new OrderFailure(404,"ORDER_NOT_FOUND");return o;}
 public MarketOrder byIntent(String user,String intent){PurchaseConditions.id(user);PurchaseConditions.id(intent);var o=repo.byIntent(user,source,channel,intent);if(o==null)throw new OrderFailure(404,"ORDER_NOT_FOUND");return o;}
 public MarketOrder active(String user,String goods){PurchaseConditions.id(user);PurchaseConditions.id(goods);return repo.active(user,goods);}
 public List<MarketOrder> list(String user,int page,int size){PurchaseConditions.id(user);if(page<1||size<1||size>100)throw PurchaseConditions.invalid();return repo.list(user,page,size);}
 public long count(String user){PurchaseConditions.id(user);return repo.count(user);}
 private static OrderFailure failure(String code){return new OrderFailure(409,code);}
 public static String hash(String... values){try{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(String.join("\n",values).getBytes(StandardCharsets.UTF_8)));}catch(Exception e){throw new IllegalStateException(e);}}
}
