package cn.zj.zjmarket.domain.order.model.valobj;
import java.util.List;
public record DiscoveryPage(String state,String reason,String goodsId,String productVersion,String activityId,String serverTime,List<DiscoveryItem> items,String activeOrderId,String nextCursor,boolean hasMore) {
 public static DiscoveryPage unavailable(String reason,String goods,String version){return new DiscoveryPage("UNAVAILABLE",reason,goods,version,null,null,List.of(),null,null,false);}
 public static DiscoveryPage active(String goods,String version,String order){return new DiscoveryPage("ACTIVE_PURCHASE",null,goods,version,null,null,List.of(),order,null,false);}
}
