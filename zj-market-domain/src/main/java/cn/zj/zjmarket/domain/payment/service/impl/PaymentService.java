package cn.zj.zjmarket.domain.payment.service.impl;
import cn.zj.zjmarket.domain.payment.adapter.repository.*;
import cn.zj.zjmarket.domain.payment.adapter.port.*;
import cn.zj.zjmarket.domain.payment.model.valobj.*;
import cn.zj.zjmarket.domain.payment.model.valobj.PaymentRules;
import cn.zj.zjmarket.domain.payment.service.IPaymentService;
import cn.zj.zjmarket.domain.order.adapter.port.ITradePort;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
import cn.zj.zjmarket.domain.order.model.valobj.TradeDispatch;
import cn.zj.zjmarket.domain.order.service.impl.OrderService;
import cn.zj.zjmarket.types.exception.OrderFailure;
import java.util.*;
public final class PaymentService implements IPaymentService {
 private final IPaymentRepository repo;private final ISimulatedChannel channel;private final ITradePort trade;private final boolean enabled;private final long rtt,ttl,skew;
 public PaymentService(IPaymentRepository repo,ISimulatedChannel channel,ITradePort trade,boolean enabled,long rtt,long ttl,long skew){this.repo=repo;this.channel=channel;this.trade=trade;this.enabled=enabled;this.rtt=rtt;this.ttl=ttl;this.skew=skew;new Evidence(null,0,0,0,rtt,ttl,skew);}
 public boolean enabled(){return enabled;}
 private Evidence evidence(MarketOrder o,String request){
  long t0=repo.now(),n0=System.nanoTime();var response=trade.execute(new TradeDispatch(null,o,"query",request,null));long elapsed=System.nanoTime()-n0,t1=repo.now();
  if(!"0000".equals(response.code())||response.evidence()==null)throw new OrderFailure(503,"PAYMENT_DEPENDENCY_UNAVAILABLE");
  var e=new Evidence(response.evidence(),t0,t1,elapsed,rtt,ttl,skew);e.validate(o,t1);return e;
 }
 private Accepted replay(String actor,String key,String hash){var op=repo.operation(actor,key);if(op==null)return null;if(!op.hash().equals(hash))throw PaymentRules.conflict("IDEMPOTENCY_CONFLICT");return new Accepted(op.receipt(),true);}
 private boolean locallyEligible(MarketOrder o){return "WAITING_PAYMENT".equals(o.businessStatus())&&!o.reviewRequired()&&o.evidence()!=null&&"RESERVATION".equals(o.evidence().recordKind());}
 private void open(){if(!enabled)throw new OrderFailure(503,"PAYMENT_DISABLED");}
 public Accepted create(String actor,String order,String key,String previous,String request){
  PaymentRules.id(order);PaymentRules.id(key);if(previous!=null)PaymentRules.id(previous);
  var o=repo.order(actor,order);String hash=OrderService.hash("CREATE_ATTEMPT",order,Objects.toString(previous,"NULL"));var old=replay(actor,key,hash);if(old!=null)return old;open();
  return repo.accept(actor,order,null,null,key,previous,null,hash,locallyEligible(o)?evidence(o,request):null);
 }
 public Accepted choose(String actor,String payment,String attempt,String key,String result,String request){
  PaymentRules.id(payment);PaymentRules.id(attempt);PaymentRules.id(key);if(!Set.of("SUCCEEDED","FAILED").contains(Objects.toString(result,"")))throw new OrderFailure(400,"VALIDATION_FAILED");
  var p=repo.payment(actor,payment);find(p,attempt);String hash=OrderService.hash("CHOOSE_RESULT",p.orderId(),payment,attempt,result);var old=replay(actor,key,hash);if(old!=null)return old;open();
  var o=repo.order(actor,p.orderId());return repo.accept(actor,p.orderId(),payment,attempt,key,null,result,hash,locallyEligible(o)?evidence(o,request):null);
 }
 public void tick(int size){for(String id:repo.due(size)){var w=repo.claim(id);if(w==null)continue;try{
   var p=repo.payment(w.actor(),id);var a=find(p,w.attemptId());var actual=channel.query(id,a.attemptId());
   // A known channel fact survives a crash or expired A window. Never call A to discard it.
   if(actual==null||w.action().equals("CHOOSE_RESULT")&&actual.state().equals("OPEN")){
    var o=repo.order(w.actor(),w.orderId());var e=evidence(o,UUID.randomUUID().toString());
    if(!repo.canDispatch(w))throw new OrderFailure(503,"PAYMENT_DISPATCH_BLOCKED");
    if(actual==null)actual=channel.create(p,a,o,e);
    if(w.action().equals("CHOOSE_RESULT")&&actual.state().equals("OPEN"))actual=channel.choose(p,a,o,e,w.result());
   }
   repo.finish(w,actual);
  }catch(OrderFailure e){repo.retry(w,e.code());}catch(Exception e){repo.retry(w,"PAYMENT_DEPENDENCY_UNAVAILABLE");}}}
 private Attempt find(Payment p,String id){var a=repo.attempt(p.paymentId(),id);if(a==null)throw new OrderFailure(404,"PAYMENT_ATTEMPT_NOT_FOUND");return a;}
 public Map<String,Object> summary(String actor,String order){var p=repo.forOrder(actor,order);if(p==null)return null;var full=view(p);var m=new LinkedHashMap<String,Object>();for(String key:List.of("paymentId","fundsState","gate","aAcceptance","amount","currency","paidAt","allowedActions","reviewRequired","errorCode"))m.put(key,full.get(key));return m;}
 public Map<String,Object> forOrder(String actor,String id){PaymentRules.id(id);var o=repo.order(actor,id);var p=repo.forOrder(actor,id);var m=new LinkedHashMap<String,Object>();m.put("orderId",id);m.put("payment",p==null?null:view(p));m.put("canCreateAttempt",enabled&&locallyEligible(o)&&repo.now()+skew<cn.zj.zjmarket.domain.order.model.valobj.ReservationEvidence.instant(o.evidence().paymentDeadline())&&(p==null||canCreate(p)));m.put("simulated",true);m.put("notice","模拟支付，不产生真实扣款");return m;}
 public Map<String,Object> payment(String actor,String id){PaymentRules.id(id);return view(repo.payment(actor,id));}
 public Map<String,Object> attempt(String actor,String payment,String attempt){PaymentRules.id(payment);PaymentRules.id(attempt);var p=repo.payment(actor,payment);return attemptView(p,find(p,attempt));}
 public Map<String,Object> operation(String actor,String order,String key){PaymentRules.id(order);PaymentRules.id(key);repo.order(actor,order);var op=repo.operation(actor,key);if(op==null||!op.receipt().orderId().equals(order))throw new OrderFailure(404,"PAYMENT_OPERATION_NOT_FOUND");var m=new LinkedHashMap<String,Object>();m.put("receipt",receipt(op.receipt()));m.put("progress",op.progress());m.put("attempt",op.receipt().attemptId()==null?null:attempt(actor,op.receipt().paymentId(),op.receipt().attemptId()));return m;}
 private boolean canCreate(Payment p){if(repo.now()+skew>=p.paymentDeadline()||p.reviewRequired()||!p.gate().equals("OPEN")||!p.fundsState().equals("UNPAID"))return false;return p.activeAttemptId()==null||find(p,p.activeAttemptId()).state().equals("FAILED");}
 private Map<String,Object> view(Payment p){var m=new LinkedHashMap<String,Object>();m.put("paymentId",p.paymentId());m.put("orderId",p.orderId());m.put("version",Long.toString(p.version()));m.put("simulated",true);m.put("fundsState",p.fundsState());m.put("gate",p.gate());m.put("aAcceptance",p.aAcceptance());m.put("amount",p.amount());m.put("currency",p.currency());m.put("paymentDeadline",time(p.paymentDeadline()));m.put("paidAt",time(p.paidAt()));m.put("activeAttemptId",p.activeAttemptId());m.put("successAttemptId",p.successAttemptId());m.put("attempts",repo.attempts(p.paymentId()).stream().map(a->attemptView(p,a)).toList());var actions=new ArrayList<String>();if(enabled&&canCreate(p))actions.add("CREATE_ATTEMPT");if(enabled&&repo.now()+skew<p.paymentDeadline()&&p.activeAttemptId()!=null&&find(p,p.activeAttemptId()).state().equals("OPEN")&&p.gate().equals("OPEN"))actions.add("SELECT_RESULT");m.put("allowedActions",actions);m.put("reviewRequired",p.reviewRequired());m.put("errorCode",p.errorCode());return m;}
 private Map<String,Object> attemptView(Payment p,Attempt a){var m=new LinkedHashMap<String,Object>();m.put("orderId",p.orderId());m.put("paymentId",p.paymentId());m.put("attemptId",a.attemptId());m.put("attemptNo",Integer.toString(a.attemptNo()));m.put("version",Long.toString(a.version()));m.put("state",a.state());m.put("amount",a.amount());m.put("currency","CNY");m.put("paymentDeadline",time(a.paymentDeadline()));m.put("paidAt",time(a.paidAt()));m.put("channelTransactionId",a.channelTransactionId());m.put("canSelectResult",enabled&&repo.now()+skew<p.paymentDeadline()&&a.state().equals("OPEN")&&p.gate().equals("OPEN")&&!p.reviewRequired());m.put("errorCode",a.errorCode());return m;}
 public static Map<String,Object> receipt(Receipt r){var m=new LinkedHashMap<String,Object>();m.put("operationId",r.operationId());m.put("action",r.action());m.put("orderId",r.orderId());m.put("paymentId",r.paymentId());m.put("attemptId",r.attemptId());m.put("accepted",r.accepted());m.put("receivedAt",time(r.receivedAt()));m.put("errorCode",r.errorCode());return m;}
 public static String time(Long ms){return ms==null?null:new java.time.format.DateTimeFormatterBuilder().appendInstant(3).toFormatter().format(java.time.Instant.ofEpochMilli(ms));}
}
