package cn.zj.zjmarket.domain.order.service.impl;
import cn.zj.zjmarket.domain.order.adapter.repository.IOrderLifecycleRepository;
import cn.zj.zjmarket.domain.order.service.IOrderLifecycleService;
import cn.zj.zjmarket.domain.order.model.valobj.*;
import java.util.Map;
public final class OrderLifecycleService implements IOrderLifecycleService {
 private final IOrderLifecycleRepository repo;public OrderLifecycleService(IOrderLifecycleRepository repo){this.repo=repo;}
 public boolean paymentCancelAllowed(cn.zj.zjmarket.domain.order.model.entity.MarketOrder o){return repo.paymentCancelAllowed(o);}
 public OrderActionResult cancel(String a,String o,String k,String r){PurchaseConditions.id(a);PurchaseConditions.id(o);PurchaseConditions.id(k);OrderControl.reason(r);return repo.cancel(a,o,k,r);}
 public Map<String,Object> coordination(String a,String o){PurchaseConditions.id(a);PurchaseConditions.id(o);return repo.coordination(a,o);}
 public Map<String,Object> exceptions(String a,int p,int s,String status,Boolean paused,Boolean review){PurchaseConditions.id(a);if(p<1||s<1||s>100||status!=null&&!java.util.Set.of("PROCESSING","WAITING_PAYMENT","CLOSING","CLOSED").contains(status))throw PurchaseConditions.invalid();return repo.exceptions(a,p,s,status,paused,review);}
 public OrderActionResult control(String a,String o,OrderControl c){PurchaseConditions.id(a);PurchaseConditions.id(o);return repo.control(a,o,c);}
}
