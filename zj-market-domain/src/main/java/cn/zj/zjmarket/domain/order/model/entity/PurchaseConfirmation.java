package cn.zj.zjmarket.domain.order.model.entity;
import cn.zj.zjmarket.domain.order.model.valobj.PurchaseConditions;
public record PurchaseConfirmation(String confirmationId,String userId,String source,String channel,PurchaseConditions conditions,String goodsName,String imageUrl,long issuedAt,long expiresAt,Long boundAt) {}
