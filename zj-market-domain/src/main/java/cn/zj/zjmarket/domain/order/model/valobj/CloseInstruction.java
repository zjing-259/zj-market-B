package cn.zj.zjmarket.domain.order.model.valobj;
public record CloseInstruction(String source,String channel,String userId,String outTradeNo,String closeId,String reason,String paymentDisposition,String verifiedAt) {}
