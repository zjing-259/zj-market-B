package cn.zj.zjmarket.domain.order.adapter.repository;
import cn.zj.zjmarket.domain.order.model.entity.*;
import cn.zj.zjmarket.domain.order.model.valobj.PurchaseConditions;
import cn.zj.zjmarket.domain.inventory.model.entity.InventoryAccount;
import cn.zj.zjmarket.domain.product.model.entity.Product;
import java.util.List;
import java.util.function.Supplier;
public interface IOrderRepository {
 <T>T transaction(Supplier<T> work);
 void lockBuyer(String userId);
 Product lockSaleProduct(PurchaseConditions conditions);
 String lockGuard(String user,String goods,long now);
 PurchaseConfirmation confirmation(String id,boolean lock);
 InventoryAccount lockInventory(String goods);
 long now();
 void insertConfirmation(PurchaseConfirmation confirmation);
 MarketOrder byIntent(String user,String source,String channel,String intent);
 MarketOrder byId(String user,String id);
 MarketOrder active(String user,String goods);
 List<MarketOrder> list(String user,int page,int size);
 long count(String user);
 boolean bound(String confirmationId);
 void create(MarketOrder order,InventoryAccount before,InventoryAccount after);
}
