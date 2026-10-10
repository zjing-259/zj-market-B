package cn.zj.zjmarket.domain.order.service;
import cn.zj.zjmarket.domain.order.model.entity.*;
import cn.zj.zjmarket.domain.order.model.valobj.*;
import java.util.List;
public interface IOrderService {
 PurchaseConfirmation confirm(String user,PurchaseConditions conditions,String requestId);
 OrderWrite create(String user,String intent,String confirmationId,String requestId);
 MarketOrder detail(String user,String orderId);
 MarketOrder byIntent(String user,String intent);
 MarketOrder active(String user,String goods);
 List<MarketOrder> list(String user,int page,int size);
 long count(String user);
}
