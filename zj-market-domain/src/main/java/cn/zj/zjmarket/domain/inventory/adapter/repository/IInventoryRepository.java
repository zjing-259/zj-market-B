package cn.zj.zjmarket.domain.inventory.adapter.repository;
import java.util.function.Supplier;
import java.util.List;
import cn.zj.zjmarket.domain.inventory.model.entity.InventoryAccount;
import cn.zj.zjmarket.domain.inventory.model.valobj.*;
public interface IInventoryRepository {
 <T>T transaction(Supplier<T> work);
 void lockOperator(String userId); boolean lockProduct(String goodsId);boolean productExists(String goodsId);
 InventoryAccount get(String goodsId,boolean lock);InventoryResult operation(String actor,String operationId);
 long now();void save(String actor,InventoryResult result,InventoryAccount before);
 List<InventoryAccount> list(int page,int size,String goodsId);long count(String goodsId);
 List<InventoryLedger> ledger(String goodsId,int page,int size);long ledgerCount(String goodsId);
}
