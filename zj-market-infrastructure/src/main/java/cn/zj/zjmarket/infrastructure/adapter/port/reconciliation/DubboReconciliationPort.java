package cn.zj.zjmarket.infrastructure.adapter.port.reconciliation;
import cn.bugstack.api.v2.*;
import cn.zj.zjmarket.domain.reconciliation.adapter.port.IReconciliationPort;
import cn.zj.zjmarket.domain.reconciliation.model.Reconciliation;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
import cn.zj.zjmarket.infrastructure.adapter.port.order.DubboTradePort;
import cn.zj.zjmarket.infrastructure.config.properties.RpcSettings;
import cn.zj.zjmarket.infrastructure.gateway.rpc.RpcClientFactory;
import cn.zj.zjmarket.infrastructure.gateway.codec.ContractCodec;
import cn.zj.zjmarket.types.exception.OrderFailure;
import org.apache.dubbo.config.ReferenceConfig;
import org.apache.dubbo.rpc.RpcContext;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import java.util.*;
import java.util.function.Supplier;

/** TLS + signed RPC; replies are typed RPC evidence, never fabricated MQ events. */
public final class DubboReconciliationPort implements IReconciliationPort,AutoCloseable {
 private final RpcSettings settings;private final ReferenceConfig<TeamService> teams;private final ReferenceConfig<TradeService> trades;
 public DubboReconciliationPort(RpcSettings s,RpcClientFactory f){settings=s;teams=f.reference(TeamService.class);trades=f.reference(TradeService.class);teams.setCheck(false);trades.setCheck(false);teams.setTimeout(10000);trades.setTimeout(10000);teams.setRetries(0);trades.setRetries(0);}
 private void scope(BaseRequest r){r.setSource(settings.getSource());r.setChannel(settings.getChannel());}
 public Reconciliation.Team team(String id){var q=new TeamQueryRequest();scope(q);q.setTeamId(id);var t=call(TeamService.class,"query",q,()->teams.get().query(q));Reconciliation.require(t!=null&&settings.getSource().equals(t.getSource())&&settings.getChannel().equals(t.getChannel()));var v=new Reconciliation.Team(t.getTeamId(),t.getTeamStatus(),t.getTeamVersion(),t.getGoodsId(),t.getActivityId(),t.getValidEndTime(),t.getServerTime());v.validate(id);return v;}
 public Reconciliation.Roster roster(String team){var q=new ReconciliationQueryRequest();scope(q);q.setTeamId(team);var r=call(TeamService.class,"queryReconciliation",q,()->teams.get().queryReconciliation(q));Reconciliation.require(r!=null&&r.getMembers()!=null);var members=new ArrayList<Reconciliation.Member>();for(var m:r.getMembers()){Reconciliation.require(m!=null);members.add(new Reconciliation.Member(m.getUserId(),m.getOutTradeNo(),m.getOrderId(),m.getOrderStatus(),m.getReservedAt(),m.getPaymentDeadline(),m.getPayPrice(),m.getCurrency(),paid(m.getPayment())));}var result=new Reconciliation.Roster(r.getReconciliationId(),r.getRosterVersion(),r.getTeamStatus(),r.getTeamVersion(),r.getValidEndTime(),members);result.validate();return result;}
 public Reconciliation.Trade trade(MarketOrder o){var q=new TradeQueryRequest();scope(q);q.setOutTradeNo(o.orderId());q.setUserId(o.confirmation().userId());var r=call(TradeService.class,"query",q,()->trades.get().query(q));var result=new Reconciliation.Trade(DubboTradePort.map(r),paid(r.getPayment()));result.validate(o);return result;}
 private Reconciliation.Paid paid(Payment p){return p==null?null:new Reconciliation.Paid(p.getPaymentId(),p.getPaidAmount(),p.getCurrency(),p.getPaidAt());}
 public Reconciliation.Result complete(Reconciliation.Completion c){Reconciliation.require(settings.getSource().equals(c.source())&&settings.getChannel().equals(c.channel()));var q=new ReconciliationCompleteRequest();scope(q);q.setTeamId(c.teamId());q.setReconciliationId(c.reconciliationId());q.setRosterVersion(c.rosterVersion());q.setCompletionId(c.completionId());q.setCheckedAt(c.checkedAt());var results=new ArrayList<ReconciliationDecision>();for(var d:c.results()){d.validate();var x=new ReconciliationDecision();x.setUserId(d.userId());x.setOutTradeNo(d.outTradeNo());x.setDisposition(d.disposition());x.setPaymentId(d.paymentId());x.setCloseId(d.closeId());x.setPaidAt(d.paidAt());x.setPaidAmount(d.paidAmount());x.setCurrency(d.currency());x.setRefundId(d.refundId());results.add(x);}q.setResults(results);var a=call(TeamService.class,"completeReconciliation",q,()->teams.get().completeReconciliation(q));Reconciliation.require(a!=null);var v=new Reconciliation.Result(a.getTeamId(),a.getReconciliationId(),a.getTeamStatus(),a.getTeamVersion(),a.getResolvedAt());v.validate(c);return v;}
 private <T>T call(Class<?> type,String method,Object request,Supplier<RpcResult<T>> action){
  if(TransactionSynchronizationManager.isActualTransactionActive())throw new IllegalStateException("Reconciliation RPC under business transaction");
  try{String id=UUID.randomUUID().toString(),time=Long.toString(System.currentTimeMillis());byte[] random=new byte[24];new java.security.SecureRandom().nextBytes(random);String nonce=Base64.getUrlEncoder().withoutPadding().encodeToString(random);String canonical=String.join("\n",settings.getClientId(),settings.getKeyId(),time,nonce,id,type.getName(),method,settings.getVersion(),settings.getGroup(),ContractCodec.sha256(new ContractCodec().encode(request)));var headers=Map.of("clientId",settings.getClientId(),"keyId",settings.getKeyId(),"timestamp",time,"nonce",nonce,"requestId",id,"signature",ContractCodec.hmac(settings.getSecret(),canonical));RpcResult<T> r;try{headers.forEach((k,v)->RpcContext.getClientAttachment().setAttachment(k,v));r=action.get();}finally{RpcContext.getClientAttachment().clearAttachments();}Reconciliation.require(r!=null&&id.equals(r.getRequestId())&&r.getCode()!=null&&r.getCode().matches("[A-Z0-9_]{1,64}"));if(!"0000".equals(r.getCode()))throw new OrderFailure(503,r.getCode());return r.getData();
  }catch(OrderFailure|IllegalArgumentException e){throw e;}catch(Exception e){throw new OrderFailure(503,"RECONCILIATION_RPC_UNAVAILABLE");}
 }
 public void close(){teams.destroy();trades.destroy();}
}
