package cn.zj.zjmarket.domain.order.service;
import cn.zj.zjmarket.domain.order.model.valobj.DiscoveryPage;
public interface ITeamDiscoveryService { DiscoveryPage list(String user,String goods,int limit,String cursor,String requestId); }
