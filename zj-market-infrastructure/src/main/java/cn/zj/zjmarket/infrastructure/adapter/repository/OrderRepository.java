package cn.zj.zjmarket.infrastructure.adapter.repository;
import cn.zj.zjmarket.domain.order.adapter.repository.IOrderRepository;
import cn.zj.zjmarket.domain.order.model.entity.*;
import cn.zj.zjmarket.domain.order.model.valobj.PurchaseConditions;
import cn.zj.zjmarket.domain.order.service.impl.OrderService;
import cn.zj.zjmarket.domain.inventory.model.entity.InventoryAccount;
import cn.zj.zjmarket.domain.product.model.entity.Product;
import cn.zj.zjmarket.domain.product.model.valobj.*;
import cn.zj.zjmarket.infrastructure.dao.*;
import cn.zj.zjmarket.infrastructure.dao.po.*;
import cn.zj.zjmarket.types.exception.*;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.dao.DuplicateKeyException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.*;
import java.util.function.Supplier;
public final class OrderRepository implements IOrderRepository {
 private final IOrderDao dao;private final IProductDao products;private final IInventoryDao stock;private final TransactionTemplate tx;private final ObjectMapper json=new ObjectMapper();
 public OrderRepository(IOrderDao dao,IProductDao products,IInventoryDao stock,TransactionTemplate tx){this.dao=dao;this.products=products;this.stock=stock;this.tx=tx;}
 public <T>T transaction(Supplier<T> work){try{return tx.execute(s->work.get());}catch(DuplicateKeyException race){return tx.execute(s->work.get());}}
 public void lockBuyer(String user){if(!Boolean.TRUE.equals(dao.enabled(user)))throw new AuthFailure(401,"AUTH_REQUIRED");if(dao.roles(user).isEmpty())throw new AuthFailure(403,"FORBIDDEN");}
 public Product lockSaleProduct(PurchaseConditions q){var r=products.get(q.goodsId(),true);if(r==null)throw new OrderFailure(404,"PRODUCT_NOT_FOUND");if(!r.saleStatus().equals("ON_SALE"))throw new OrderFailure(409,"PRODUCT_NOT_SALEABLE");if(r.version()!=Long.parseLong(q.expectedOffer().productVersion()) || r.originalPrice().compareTo(new java.math.BigDecimal(q.expectedOffer().originalPrice()))!=0)throw new OrderFailure(409,"PRODUCT_VERSION_MISMATCH");var sync=products.progress(q.goodsId());if(sync==null||!sync.ready(r.version()))throw new OrderFailure(409,"PRODUCT_SYNC_PENDING");return new Product(r.goodsId(),new ProductFields(r.goodsName(),r.description(),r.imageUrl(),r.originalPrice().toPlainString(),r.currency(),SaleStatus.valueOf(r.saleStatus())),r.version(),r.createdAt(),r.updatedAt());}
 public String lockGuard(String user,String goods,long now){dao.ensureGuard(user,goods,now);return dao.guard(user,goods);}
 public PurchaseConfirmation confirmation(String id,boolean lock){var r=dao.confirmation(id,lock);if(r==null)return null;var saved=decode(r.snapshot(),PurchaseConfirmation.class);if(!saved.confirmationId().equals(r.confirmationId())||!saved.userId().equals(r.userId())||!saved.source().equals(r.source())||!saved.channel().equals(r.channel())||!saved.conditions().goodsId().equals(r.goodsId())||saved.issuedAt()!=r.issuedAt()||saved.expiresAt()!=r.expiresAt())throw new IllegalStateException("Confirmation audit mismatch");return new PurchaseConfirmation(saved.confirmationId(),saved.userId(),saved.source(),saved.channel(),saved.conditions(),saved.goodsName(),saved.imageUrl(),saved.issuedAt(),saved.expiresAt(),r.boundAt());}
 public InventoryAccount lockInventory(String goods){var r=stock.get(goods,true);if(r==null)throw new OrderFailure(503,"INVENTORY_ACCOUNT_MISSING");return new InventoryAccount(r.goodsId(),r.available(),r.reserved(),r.sold(),r.version(),r.updatedAt());}
 public long now(){return dao.now();}
 public void insertConfirmation(PurchaseConfirmation c){var q=c.conditions();one(dao.insertConfirmation(new ConfirmationRow(c.confirmationId(),c.userId(),c.source(),c.channel(),q.goodsId(),Long.parseLong(q.expectedOffer().productVersion()),Long.parseLong(q.expectedOffer().activityId()),q.mode(),q.teamId(),encode(c),c.issuedAt(),c.expiresAt(),c.boundAt())));}
 public MarketOrder byIntent(String user,String source,String channel,String intent){return order(dao.byIntent(user,source,channel,intent));}
 public MarketOrder byId(String user,String id){return order(dao.byId(user,id));}
 public MarketOrder active(String user,String goods){var id=dao.active(user,goods);return id==null?null:byId(user,id);}
 public List<MarketOrder> list(String user,int page,int size){return dao.list(user,((long)page-1)*size,size).stream().map(this::order).toList();}
 public long count(String user){return dao.count(user);}public boolean bound(String id){return dao.bound(id)>0;}
 public void create(MarketOrder o,InventoryAccount before,InventoryAccount after){
  var c=o.confirmation();var q=c.conditions();var offer=q.expectedOffer();var request=new TreeMap<String,Object>();request.put("userId",c.userId());request.put("source",c.source());request.put("channel",c.channel());request.put("outTradeNo",o.orderId());request.put("goodsId",q.goodsId());request.put("activityId",offer.activityId());request.put("productVersion",offer.productVersion());request.put("quantity",1);request.put("expectedPayPrice",offer.payPrice());request.put("currency","CNY");request.put("teamId",q.teamId());String body=encode(request);
  one(dao.insertOrder(new MarketOrderRow(o.orderId(),c.userId(),c.source(),c.channel(),o.purchaseIntentId(),o.requestHash(),c.confirmationId(),q.goodsId(),encode(c),body,OrderService.hash(body),offer.originalPrice(),offer.deductionPrice(),offer.payPrice(),o.businessStatus(),o.orderVersion(),o.createdAt(),o.reserveWaitDeadline(),o.mayHaveDispatched(),o.paymentExposure())));
  one(dao.bind(c.confirmationId(),o.createdAt()));one(stock.update(new InventoryRow(after.goodsId(),after.available(),after.reserved(),after.sold(),after.version(),after.updatedAt())));
  one(dao.reservation(o.orderId(),q.goodsId(),o.createdAt()));one(dao.task(o.orderId(),o.createdAt()));one(dao.activate(c.userId(),q.goodsId(),o.orderId(),o.createdAt()));one(dao.ledger(UUID.randomUUID().toString(),o.orderId(),before,after));
 }
 private MarketOrder order(MarketOrderRow r){if(r==null)return null;var c=decode(r.snapshot(),PurchaseConfirmation.class);if(!c.userId().equals(r.userId())||!c.source().equals(r.source())||!c.channel().equals(r.channel())||!c.conditions().goodsId().equals(r.goodsId())||!c.confirmationId().equals(r.confirmationId())||!OrderService.hash(r.userId(),r.source(),r.channel(),r.purchaseIntentId(),r.confirmationId()).equals(r.requestHash()))throw new IllegalStateException("Order audit mismatch");var evidence=r.evidence()==null?null:decode(r.evidence(),cn.zj.zjmarket.domain.order.model.valobj.ReservationEvidence.class);if(evidence!=null&&!OrderService.hash(encode(evidence)).equals(r.evidenceHash()))throw new IllegalStateException("A evidence audit mismatch");return new MarketOrder(r.orderId(),r.purchaseIntentId(),r.requestHash(),c,r.businessStatus(),r.orderVersion(),r.createdAt(),r.reserveWaitDeadline(),r.mayHaveDispatched(),r.paymentExposure(),evidence,r.updatedAt(),r.reviewRequired(),r.errorCode(),r.closedAt(),r.closeBasis());}
 private String encode(Object v){try{return json.writeValueAsString(v);}catch(Exception e){throw new IllegalStateException("Order serialization failed",e);}}
 private <T>T decode(String v,Class<T> type){try{return json.readValue(v,type);}catch(Exception e){throw new IllegalStateException("Order serialization invalid",e);}}
 private static void one(int n){if(n!=1)throw new IllegalStateException("Order atomic write mismatch");}
}
