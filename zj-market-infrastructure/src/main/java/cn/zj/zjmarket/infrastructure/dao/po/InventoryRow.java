package cn.zj.zjmarket.infrastructure.dao.po;
public record InventoryRow(String goodsId,long available,long reserved,long sold,long version,long updatedAt) {}
