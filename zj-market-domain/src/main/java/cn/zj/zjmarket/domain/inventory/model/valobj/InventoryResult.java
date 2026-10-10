package cn.zj.zjmarket.domain.inventory.model.valobj;
import cn.zj.zjmarket.domain.inventory.model.entity.InventoryAccount;
public record InventoryResult(String operationId,InventoryRequest request,String outcome,String code,String message,long completedAt,InventoryAccount inventory) {}
