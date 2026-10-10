package cn.zj.zjmarket.domain.payment.service;
import cn.zj.zjmarket.domain.payment.model.valobj.*;
import java.util.*;
public interface IPaymentService {
 Map<String,Object> summary(String actor,String order);
 Map<String,Object> forOrder(String actor,String order);
 Map<String,Object> payment(String actor,String payment);
 Map<String,Object> attempt(String actor,String payment,String attempt);
 Map<String,Object> operation(String actor,String order,String operation);
 Accepted create(String actor,String order,String key,String previous,String request);
 Accepted choose(String actor,String payment,String attempt,String key,String result,String request);
 void tick(int size);
 boolean enabled();
}
