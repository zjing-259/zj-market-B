package cn.zj.zjmarket.domain.payment.adapter.port;
import cn.zj.zjmarket.domain.payment.model.valobj.*;
public interface ISettlementTransport {
 void start() throws Exception;
 void publish(TradeDelivery work);
 TradeReceipt query(TradeDelivery work);
 TradeReceipt queryTrade(TradeDelivery work);
}
