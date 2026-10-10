package cn.zj.zjmarket.infrastructure.dao.po;
public record InventoryOperationRow(String rowId,String actor,String operationId,String kind,String goodsId,long delta,long expectedVersion,String reason,String outcome,String code,long completedAt,long available,long reserved,long sold,long version,long inventoryUpdatedAt,String requestHash) {}
