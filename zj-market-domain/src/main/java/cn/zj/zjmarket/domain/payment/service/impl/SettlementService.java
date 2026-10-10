package cn.zj.zjmarket.domain.payment.service.impl;
import cn.zj.zjmarket.domain.payment.adapter.port.*;
import cn.zj.zjmarket.domain.payment.adapter.repository.ISettlementRepository;
import cn.zj.zjmarket.domain.payment.service.ISettlementService;
import cn.zj.zjmarket.domain.order.service.impl.OrderService;
import cn.zj.zjmarket.domain.payment.model.valobj.Channel;
import java.util.Objects;
public final class SettlementService implements ISettlementService {
 private final ISettlementRepository repo;private final IChannelFacts channel;private final ISettlementTransport transport;
 public SettlementService(ISettlementRepository repo,IChannelFacts channel,ISettlementTransport transport){this.repo=repo;this.channel=channel;this.transport=transport;}
 public void tick(int size){
  for(var n:channel.notices(size)){
   try{var f=channel.fact(n.paymentId(),n.attemptId());
    // Notification is a durable wake-up. Only the original channel query can supply the fact.
    if(f==null)continue;
    if(!OrderService.hash(n.body()).equals(n.hash())||!Objects.equals(f.channel(),n.observed())){repo.quarantine(n.id(),"SIMULATED_CHANNEL","NOTICE",null,null,n.body().getBytes(java.nio.charset.StandardCharsets.UTF_8),"NOTICE_HASH_MISMATCH");channel.acknowledge(n,true);continue;}
    repo.observe(f);channel.acknowledge(n,false);
   }catch(RuntimeException failure){try{if(n.failures()>=5)repo.noticeFailed(n);channel.retry(n);}catch(RuntimeException unavailable){/* No ACK: durable lease expires and recovery continues. */}}
  }
  // Query compensation is independent of notification state or a lost ACK.
  for(var a:repo.unresolved(size)){var f=channel.fact(a[0],a[1]);if(f!=null)repo.observe(f);}
  repo.applyInbox(size);
  for(int i=0;i<size;i++){var w=repo.claim();if(w==null)break;
   try{cn.zj.zjmarket.domain.payment.model.valobj.TradeReceipt result=null;
    if(!w.state().equals("READY")||w.failures()>0){try{result=transport.query(w);if(result==null)result=transport.queryTrade(w);}catch(RuntimeException unavailable){if(!w.state().equals("READY"))throw unavailable;}}
    if(result!=null){repo.receive(result);repo.delivered(w,false,null);}
    else if(w.state().equals("READY")){transport.publish(w);repo.delivered(w,true,null);}
    else repo.delivered(w,false,"RESULT_PENDING");
   }catch(RuntimeException failure){repo.delivered(w,false,"TRADE_DEPENDENCY_UNAVAILABLE");}
  }
  repo.applyInbox(size);
 }
}
