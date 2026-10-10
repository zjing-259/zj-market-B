package cn.zj.zjmarket.domain.order.service.impl;
import cn.zj.zjmarket.domain.order.service.ITeamService;
import cn.zj.zjmarket.domain.order.adapter.port.ITradePort;
import cn.zj.zjmarket.domain.order.adapter.repository.IOrderRepository;
import cn.zj.zjmarket.domain.order.model.valobj.*;
public final class TeamService implements ITeamService {
 private final ITradePort port;private final IOrderRepository orders;
 public TeamService(ITradePort port,IOrderRepository orders){this.port=port;this.orders=orders;}
 public TeamView query(String user,String team,String request){PurchaseConditions.id(user);PurchaseConditions.id(team);var t=port.team(user,team,request);String own=t.myOrderId();if(own!=null){var order=orders.byId(user,own);if(order==null)own=null;else if(order.evidence()!=null&&!team.equals(order.evidence().teamId())||"JOIN".equals(order.confirmation().conditions().mode())&&!team.equals(order.confirmation().conditions().teamId()))throw new cn.zj.zjmarket.types.exception.OrderFailure(502,"UPSTREAM_RESPONSE_INVALID");}return new TeamView(t.teamId(),t.goodsId(),t.activityId(),t.status(),t.version(),t.targetCount(),t.reservedCount(),t.paidCount(),t.validStartTime(),t.validEndTime(),t.serverTime(),t.joinable(),own);}
}
