package cn.zj.zjmarket.domain.payment.adapter.repository;
import cn.zj.zjmarket.domain.payment.model.valobj.*;
import java.util.*;
public interface IFulfillmentRepository {
 List<String> due(int size);
 FulfillmentWork claim(String id);
 void complete(FulfillmentWork work,TradeReceipt currentTrade);
 void retry(FulfillmentWork work);
 Map<String,Object> summary(String user,String order);
}
