package cn.zj.zjmarket.domain.order.adapter.repository;
import cn.zj.zjmarket.domain.order.model.valobj.*;
import java.util.Map;
public interface IOrderLifecycleRepository {
 default boolean paymentCancelAllowed(cn.zj.zjmarket.domain.order.model.entity.MarketOrder order){return false;}
 OrderActionResult cancel(String actor,String order,String key,String reason);
 Map<String,Object> coordination(String actor,String order);
 Map<String,Object> exceptions(String actor,int page,int size,String status,Boolean paused,Boolean review);
 OrderActionResult control(String actor,String order,OrderControl control);
}
