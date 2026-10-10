package cn.zj.zjmarket.domain.inventory.service;
import cn.zj.zjmarket.domain.inventory.model.entity.InventoryAccount;
import cn.zj.zjmarket.domain.inventory.model.valobj.*;
public interface IInventoryService {
 InventoryWrite execute(String actor,String operationId,InventoryRequest request);
 InventoryResult operation(String actor,String operationId);
 InventoryAccount detail(String goodsId);InventoryPage<InventoryAccount> list(int page,int size,String goodsId);
 InventoryPage<InventoryLedger> ledger(String goodsId,int page,int size);
}
