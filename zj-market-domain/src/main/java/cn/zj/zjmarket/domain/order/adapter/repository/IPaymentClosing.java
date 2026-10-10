package cn.zj.zjmarket.domain.order.adapter.repository;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
import cn.zj.zjmarket.domain.order.model.valobj.TradeLease;
public interface IPaymentClosing {
 boolean eligible(MarketOrder order);
 boolean begin(MarketOrder order,String reason,String code,long now);
 boolean prepare(TradeLease lease);
 boolean proven(MarketOrder order);
}
