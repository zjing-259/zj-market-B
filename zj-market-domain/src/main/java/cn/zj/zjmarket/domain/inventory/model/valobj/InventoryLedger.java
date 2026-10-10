package cn.zj.zjmarket.domain.inventory.model.valobj;
public record InventoryLedger(String ledgerId,String goodsId,String operationId,String kind,long delta,long beforeAvailable,long afterAvailable,long reserved,long sold,String reason,long createdAt,String actorId,Long beforeReserved,Long beforeSold,String orderId) {}
