package cn.zj.zjmarket.test.payment;
import cn.zj.zjmarket.trigger.job.SettlementJob;
import cn.zj.zjmarket.domain.payment.adapter.port.ISettlementTransport;
import cn.zj.zjmarket.domain.payment.adapter.repository.IFulfillmentRepository;
import cn.zj.zjmarket.domain.payment.model.valobj.*;
import cn.zj.zjmarket.domain.payment.service.impl.FulfillmentService;
import org.junit.jupiter.api.Test;
import java.util.*;
import java.util.concurrent.*;
import static org.junit.jupiter.api.Assertions.*;
class SettlementJobTest {
 @Test void unavailableSubscriptionsAndSettlementDoNotStarveFulfillment() throws Exception {
  var visited=new CountDownLatch(2);
  var transport=new ISettlementTransport(){
   public void start(){throw new IllegalStateException("broker offline");}
   public void publish(TradeDelivery w){throw new AssertionError();}
   public TradeReceipt query(TradeDelivery w){throw new AssertionError();}
   public TradeReceipt queryTrade(TradeDelivery w){throw new AssertionError();}
  };
  var repo=new IFulfillmentRepository(){
   public List<String> due(int size){visited.countDown();throw new IllegalStateException("temporary fulfillment failure");}
   public FulfillmentWork claim(String id){throw new AssertionError();}
   public void complete(FulfillmentWork w,TradeReceipt r){throw new AssertionError();}
   public void retry(FulfillmentWork w){throw new AssertionError();}
   public Map<String,Object> summary(String u,String o){throw new AssertionError();}
  };
  var job=new SettlementJob(size->{throw new IllegalStateException("settlement offline");},transport,true);
  job.enableFulfillment(new FulfillmentService(repo,transport));
  try {job.start();assertTrue(visited.await(8,TimeUnit.SECONDS),"both recovery rounds must visit fulfillment despite other failures");}
  finally {job.stop();}
  assertFalse(job.isRunning());
 }
}
