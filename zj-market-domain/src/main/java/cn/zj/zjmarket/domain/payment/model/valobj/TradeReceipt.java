package cn.zj.zjmarket.domain.payment.model.valobj;
public record TradeReceipt(String producer,String eventId,String type,String hash,String body,String originalEventId){}
