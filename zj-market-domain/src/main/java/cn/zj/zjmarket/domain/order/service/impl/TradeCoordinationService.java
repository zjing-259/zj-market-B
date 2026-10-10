package cn.zj.zjmarket.domain.order.service.impl;
import cn.zj.zjmarket.domain.order.adapter.repository.ITradeRepository;
import cn.zj.zjmarket.domain.order.adapter.port.ITradePort;
import cn.zj.zjmarket.domain.order.service.ITradeCoordinationService;
import cn.zj.zjmarket.domain.order.model.valobj.TradeReply;
public final class TradeCoordinationService implements ITradeCoordinationService {
 private final ITradeRepository repository;private final ITradePort port;private final long leaseMillis;
 public TradeCoordinationService(ITradeRepository repository,ITradePort port,long leaseMillis){this.repository=repository;this.port=port;this.leaseMillis=leaseMillis;}
 public int tick(int batch){int n=0;for(String id:repository.due(batch)){recover(id);n++;}return n;}
 public void recover(String id){var lease=repository.claim(id,leaseMillis);if(lease==null)return;var dispatch=repository.beforeSend(lease);if(dispatch==null)return;TradeReply reply;try{reply=port.execute(dispatch);if(reply==null)reply=new TradeReply("UPSTREAM_RESPONSE_INVALID",null);}catch(Exception technical){reply=new TradeReply("DEPENDENCY_UNAVAILABLE",null);}repository.complete(dispatch,reply);}
}
