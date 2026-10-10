package cn.zj.zjmarket.domain.order.adapter.port;
import cn.zj.zjmarket.domain.order.model.valobj.*;
public interface ITradePort { TradeReply execute(TradeDispatch dispatch); TeamView team(String userId,String teamId,String requestId); }
