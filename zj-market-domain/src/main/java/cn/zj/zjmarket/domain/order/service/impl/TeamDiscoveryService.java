package cn.zj.zjmarket.domain.order.service.impl;
import cn.zj.zjmarket.domain.order.adapter.port.ITeamDiscoveryPort;
import cn.zj.zjmarket.domain.order.model.valobj.DiscoveryPage;
import cn.zj.zjmarket.domain.order.service.ITeamDiscoveryService;
import cn.zj.zjmarket.domain.order.service.IOrderService;
import cn.zj.zjmarket.domain.product.service.IProductService;
import cn.zj.zjmarket.domain.product.service.IMarketingTrialService;
import cn.zj.zjmarket.domain.inventory.service.IInventoryService;
import cn.zj.zjmarket.domain.product.model.valobj.SaleStatus;
import cn.zj.zjmarket.types.exception.ProductFailure;
import java.util.Objects;
public final class TeamDiscoveryService implements ITeamDiscoveryService {
 private final IProductService products;private final IOrderService orders;private final IInventoryService stock;private final IMarketingTrialService trial;private final ITeamDiscoveryPort discovery;
 public TeamDiscoveryService(IProductService products,IOrderService orders,IInventoryService stock,IMarketingTrialService trial,ITeamDiscoveryPort discovery){this.products=products;this.orders=orders;this.stock=stock;this.trial=trial;this.discovery=discovery;}
 public DiscoveryPage list(String user,String goods,int limit,String cursor,String requestId){
  if(user==null||user.isBlank()||user.length()>64)throw new ProductFailure(401,"AUTH_REQUIRED");
  if(goods==null||!goods.matches("[A-Za-z0-9._-]{1,64}")||limit<1||limit>10)throw new ProductFailure(400,"VALIDATION_FAILED");
  discovery.validateCursor(user,goods,cursor);
  var before=products.detail(goods,false);String version=Long.toString(before.product().version());
  var active=orders.active(user,goods);if(active!=null)return DiscoveryPage.active(goods,version,active.orderId());
  if(!before.sync().ready(before.product().version()))return DiscoveryPage.unavailable("PRODUCT_SYNC_PENDING",goods,version);
  var inventory=stock.detail(goods);if(inventory==null||inventory.available()<1)return DiscoveryPage.unavailable("OUT_OF_STOCK",goods,version);
  cn.zj.zjmarket.domain.product.model.valobj.TrialResult quote;
  try{quote=trial.trial(user,goods,requestId);}catch(ProductFailure e){
   if("PRODUCT_SYNC_PENDING".equals(e.code()))return DiscoveryPage.unavailable("PRODUCT_SYNC_PENDING",goods,version);
   if("PRODUCT_VERSION_MISMATCH".equals(e.code())||"PRODUCT_VERSION_CONFLICT".equals(e.code()))throw new ProductFailure(409,"TEAM_DISCOVERY_CONTEXT_CHANGED");
   throw e;
  }
  if("NO_PUBLIC_OFFER".equals(quote.state())){if(cursor!=null)throw new ProductFailure(409,"TEAM_DISCOVERY_CONTEXT_CHANGED");return DiscoveryPage.unavailable("NO_OFFER",goods,version);}
  if("INELIGIBLE".equals(quote.state()))return DiscoveryPage.unavailable("INELIGIBLE",goods,version);
  if(!"AVAILABLE".equals(quote.state())||quote.offer()==null)throw new ProductFailure(502,"UPSTREAM_RESPONSE_INVALID");
  var page=discovery.list(user,goods,quote.offer().activityId(),version,quote.offer().targetCount(),limit,cursor,requestId);
  var after=products.detail(goods,true);
  if(after.product().version()!=before.product().version()||after.product().fields().saleStatus()!=SaleStatus.ON_SALE||!Objects.equals(after.sync().targetEventId(),before.sync().targetEventId())||!after.sync().ready(after.product().version()))throw new ProductFailure(409,"TEAM_DISCOVERY_CONTEXT_CHANGED");
  return page;
 }
}
