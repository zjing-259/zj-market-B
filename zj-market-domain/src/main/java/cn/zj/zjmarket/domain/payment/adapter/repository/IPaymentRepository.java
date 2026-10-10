package cn.zj.zjmarket.domain.payment.adapter.repository;
import cn.zj.zjmarket.domain.payment.model.valobj.*;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
import java.util.*;
public interface IPaymentRepository {
 long now();
 MarketOrder order(String actor,String id);
 Payment payment(String actor,String id);
 Payment forOrder(String actor,String order);
 List<Attempt> attempts(String payment);
 Attempt attempt(String payment,String attempt);
 boolean canDispatch(Work work);
 Operation operation(String actor,String operation);
 Accepted accept(String actor,String order,String payment,String attempt,String key,String previous,String result,String hash,Evidence evidence);
 List<String> due(int size);
 Work claim(String payment);
 void finish(Work work,Channel channel);
 void retry(Work work,String code);
}
