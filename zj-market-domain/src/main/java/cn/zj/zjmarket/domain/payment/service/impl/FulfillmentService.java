package cn.zj.zjmarket.domain.payment.service.impl;
import cn.zj.zjmarket.domain.payment.adapter.repository.IFulfillmentRepository;
import cn.zj.zjmarket.domain.payment.adapter.port.ISettlementTransport;
public final class FulfillmentService {
 private final IFulfillmentRepository repo;private final ISettlementTransport transport;
 public FulfillmentService(IFulfillmentRepository repo,ISettlementTransport transport){this.repo=repo;this.transport=transport;}
 public void tick(int size){for(String id:repo.due(size)){var w=repo.claim(id);if(w==null)continue;try{repo.complete(w,transport.queryTrade(w.payment()));}catch(RuntimeException unavailable){repo.retry(w);}}}
}
