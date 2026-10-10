package cn.zj.zjmarket.domain.payment.adapter.port;
import cn.zj.zjmarket.domain.payment.model.valobj.*;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
public interface ISimulatedChannel {
 Channel query(String payment,String attempt);
 Channel create(Payment payment,Attempt attempt,MarketOrder order,Evidence evidence);
 Channel choose(Payment payment,Attempt attempt,MarketOrder order,Evidence evidence,String result);
}
