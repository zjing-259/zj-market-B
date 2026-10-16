package cn.zj.zjmarket.domain.order.adapter.port;
import cn.zj.zjmarket.domain.order.model.valobj.DiscoveryPage;
public interface ITeamDiscoveryPort extends AutoCloseable {
 default void close() {}
 void validateCursor(String user,String goods,String cursor);
 DiscoveryPage list(String user,String goods,String activity,String version,int target,int limit,String cursor,String requestId);
}
