package cn.zj.zjmarket.domain.reconciliation.adapter.port;
import cn.zj.zjmarket.domain.reconciliation.model.Reconciliation.*;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
public interface IReconciliationPort {
 Team team(String teamId);
 Roster roster(String teamId);
 Trade trade(MarketOrder order);
 Result complete(Completion completion);
}
