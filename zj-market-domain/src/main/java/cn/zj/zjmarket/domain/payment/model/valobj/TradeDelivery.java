package cn.zj.zjmarket.domain.payment.model.valobj;
public record TradeDelivery(String eventId,String paymentId,String orderId,String userId,String body,String hash,String state,int failures,String token){}
