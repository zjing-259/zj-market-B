package cn.zj.zjmarket.domain.payment.adapter.repository;
import cn.zj.zjmarket.domain.payment.model.valobj.*;
import java.util.List;
public interface ISettlementRepository {
 void noticeFailed(ChannelNotice notice);
 void observe(ChannelFact fact);
 List<String[]> unresolved(int size);
 TradeDelivery claim();
 TradeDelivery claim(String eventId);
 void delivered(TradeDelivery work,boolean sent,String error);
 void receive(TradeReceipt receipt);
 void quarantine(String key,String topic,String tag,String keyId,String signature,byte[] body,String reason);
 void applyInbox(int size);
}
