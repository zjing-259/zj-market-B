package cn.zj.zjmarket.domain.order.service;
import cn.zj.zjmarket.domain.order.model.valobj.TeamView;
public interface ITeamService { TeamView query(String userId,String teamId,String requestId); }
