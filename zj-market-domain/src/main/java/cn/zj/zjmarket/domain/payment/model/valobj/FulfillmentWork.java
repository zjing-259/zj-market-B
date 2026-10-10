package cn.zj.zjmarket.domain.payment.model.valobj;
public record FulfillmentWork(String id,String orderId,String userId,String token,long intentVersion,TradeDelivery payment) {}
