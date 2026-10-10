package cn.zj.zjmarket.domain.order.model.valobj;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
public record TradeDispatch(TradeLease lease,MarketOrder order,String method,String requestId,String attemptId,CloseInstruction closeRequest){public TradeDispatch(TradeLease lease,MarketOrder order,String method,String requestId,String attemptId){this(lease,order,method,requestId,attemptId,null);}}
