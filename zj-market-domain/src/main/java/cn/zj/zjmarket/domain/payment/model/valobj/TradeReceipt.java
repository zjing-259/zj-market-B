package cn.zj.zjmarket.domain.payment.model.valobj;
/** authority is an authenticated typed Trade.query snapshot, independent from the event body. */
public record TradeReceipt(String producer,String eventId,String type,String hash,String body,String originalEventId,String authority){
 public TradeReceipt(String producer,String eventId,String type,String hash,String body,String originalEventId){this(producer,eventId,type,hash,body,originalEventId,null);}
}
