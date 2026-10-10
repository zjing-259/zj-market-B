package cn.zj.zjmarket.domain.order.adapter.repository;
import cn.zj.zjmarket.domain.order.model.valobj.*;
import java.util.List;
public interface ITradeRepository {
 default boolean prepare(TradeLease lease){return true;}
 List<String> due(int limit);
 TradeLease claim(String orderId,long leaseMillis);
 TradeDispatch beforeSend(TradeLease lease);
 boolean complete(TradeDispatch dispatch,TradeReply reply);
}
