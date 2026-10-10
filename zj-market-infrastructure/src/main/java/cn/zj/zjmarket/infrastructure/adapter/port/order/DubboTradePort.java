package cn.zj.zjmarket.infrastructure.adapter.port.order;
import cn.bugstack.api.v2.*;
import cn.zj.zjmarket.domain.order.adapter.port.ITradePort;
import cn.zj.zjmarket.domain.order.model.valobj.*;
import cn.zj.zjmarket.infrastructure.config.properties.RpcSettings;
import cn.zj.zjmarket.infrastructure.gateway.codec.ContractCodec;
import cn.zj.zjmarket.infrastructure.gateway.rpc.RpcClientFactory;
import cn.zj.zjmarket.types.exception.OrderFailure;
import org.apache.dubbo.config.ReferenceConfig;
import org.apache.dubbo.rpc.RpcContext;
import java.util.*;
import java.util.function.Supplier;
public final class DubboTradePort implements ITradePort,AutoCloseable {
 private final RpcSettings settings;private final ReferenceConfig<TradeService> trade;private final ReferenceConfig<TeamService> teams;
 public DubboTradePort(RpcSettings settings,RpcClientFactory factory){this.settings=settings;trade=factory.reference(TradeService.class);teams=factory.reference(TeamService.class);trade.setCheck(false);teams.setCheck(false);trade.setTimeout(10000);teams.setTimeout(10000);}
 public TradeReply execute(TradeDispatch d){try{var c=d.order().confirmation();if(!c.source().equals(settings.getSource())||!c.channel().equals(settings.getChannel()))return new TradeReply("INTEGRATION_AUTH_FAILED",null);RpcResult<Reservation> response;
  if(d.method().equals("close")){var frozen=d.closeRequest();if(frozen==null)return new TradeReply("UPSTREAM_RESPONSE_INVALID",null);var q=new CloseRequest();q.setSource(frozen.source());q.setChannel(frozen.channel());q.setUserId(frozen.userId());q.setOutTradeNo(frozen.outTradeNo());q.setCloseId(frozen.closeId());q.setReason(frozen.reason());q.setPaymentDisposition(frozen.paymentDisposition());q.setVerifiedAt(frozen.verifiedAt());var result=call(TradeService.class,"close",q,d.requestId(),()->trade.get().close(q));if(!"0000".equals(result.getCode()))return new TradeReply(result.getCode(),null);var r=result.getData();if(r==null)throw invalid();return new TradeReply("0000",null,new CloseEvidence(r.getOutTradeNo(),r.getOrderId(),r.getTeamId(),r.getOrderStatus(),r.getClosedAt(),r.getRecordVersion(),r.getTeamVersion()));}
  if(d.method().equals("reserve")){var q=new ReserveRequest();var conditions=c.conditions();var o=conditions.expectedOffer();scope(q);q.setUserId(c.userId());q.setOutTradeNo(d.order().orderId());q.setGoodsId(conditions.goodsId());q.setActivityId(o.activityId());q.setQuantity(1);q.setProductVersion(o.productVersion());q.setExpectedPayPrice(o.payPrice());q.setCurrency(o.currency());q.setTeamId(conditions.teamId());response=call(TradeService.class,"reserve",q,d.requestId(),()->trade.get().reserve(q));}
  else if(d.method().equals("query")){var q=new TradeQueryRequest();scope(q);q.setUserId(c.userId());q.setOutTradeNo(d.order().orderId());response=call(TradeService.class,"query",q,d.requestId(),()->trade.get().query(q));}else return new TradeReply("UPSTREAM_RESPONSE_INVALID",null);
  if(!"0000".equals(response.getCode()))return new TradeReply(response.getCode(),null);return new TradeReply("0000",map(response.getData()));
 }catch(OrderFailure e){return new TradeReply(e.code(),null);}catch(Exception e){return new TradeReply(technical(e),null);}}
 public TeamView team(String user,String id,String requestId){
  try{var q=new TeamQueryRequest();scope(q);q.setUserId(user);q.setTeamId(id);var response=call(TeamService.class,"query",q,requestId,()->teams.get().query(q));
   if(!"0000".equals(response.getCode())){if(Set.of("NOT_FOUND","FORBIDDEN","PRODUCT_NOT_FOUND").contains(Objects.toString(response.getCode(),"")))throw new OrderFailure(404,"TEAM_NOT_FOUND");if(Set.of("AUTH_REQUIRED","AUTH_INVALID","REPLAY_REJECTED","E0112").contains(Objects.toString(response.getCode(),"")))throw new OrderFailure(502,"INTEGRATION_AUTH_FAILED");throw new OrderFailure(503,"DEPENDENCY_UNAVAILABLE");}
   var t=response.getData();if(t==null||!id.equals(t.getTeamId())||!settings.getSource().equals(t.getSource())||!settings.getChannel().equals(t.getChannel()))throw invalid();PurchaseConditions.id(t.getGoodsId());ReservationEvidence.version(t.getActivityId());ReservationEvidence.version(t.getTeamVersion());
   if(!Set.of("FORMING","RECONCILING","COMPLETED","FAILED").contains(Objects.toString(t.getTeamStatus(),""))||t.getTargetCount()==null||t.getTargetCount()<1||t.getTargetCount()>100||t.getReservedCount()==null||t.getPaidCount()==null||t.getReservedCount()<t.getPaidCount()||t.getPaidCount()<0||t.getReservedCount()>t.getTargetCount()||t.getJoinable()==null||ReservationEvidence.instant(t.getValidEndTime())<=ReservationEvidence.instant(t.getValidStartTime()))throw invalid();ReservationEvidence.instant(t.getServerTime());
   if(t.getJoinable()&&(!"FORMING".equals(t.getTeamStatus())||t.getReservedCount()>=t.getTargetCount()||ReservationEvidence.instant(t.getServerTime())>=ReservationEvidence.instant(t.getValidEndTime())||ReservationEvidence.instant(t.getServerTime())<ReservationEvidence.instant(t.getValidStartTime())))throw invalid();
   String own=null;var r=t.getOwnReservation();if(r!=null){if(!user.equals(r.getUserId())||!settings.getSource().equals(r.getSource())||!settings.getChannel().equals(r.getChannel())||!id.equals(r.getTeamId()))throw invalid();own=r.getOutTradeNo();PurchaseConditions.id(own);}
   return new TeamView(id,t.getGoodsId(),t.getActivityId(),t.getTeamStatus(),t.getTeamVersion(),t.getTargetCount(),t.getReservedCount(),t.getPaidCount(),t.getValidStartTime(),t.getValidEndTime(),t.getServerTime(),t.getJoinable(),own);
  }catch(OrderFailure e){throw e;}catch(IllegalArgumentException e){throw invalid();}catch(Exception e){throw new OrderFailure(503,"DEPENDENCY_UNAVAILABLE");}
 }
 private void scope(BaseRequest q){q.setSource(settings.getSource());q.setChannel(settings.getChannel());}
 private <T>RpcResult<T> call(Class<?> type,String method,Object request,String requestId,Supplier<RpcResult<T>> work)throws Exception{
  byte[] random=new byte[24];new java.security.SecureRandom().nextBytes(random);String nonce=Base64.getUrlEncoder().withoutPadding().encodeToString(random),time=Long.toString(System.currentTimeMillis());String canonical=String.join("\n",settings.getClientId(),settings.getKeyId(),time,nonce,requestId,type.getName(),method,settings.getVersion(),settings.getGroup(),ContractCodec.sha256(new ContractCodec().encode(request)));
  var attachments=Map.of("clientId",settings.getClientId(),"keyId",settings.getKeyId(),"timestamp",time,"nonce",nonce,"requestId",requestId,"signature",ContractCodec.hmac(settings.getSecret(),canonical));RpcResult<T> result;try{attachments.forEach((k,v)->RpcContext.getClientAttachment().setAttachment(k,v));result=work.get();}finally{RpcContext.getClientAttachment().clearAttachments();}
  if(result==null||!requestId.equals(result.getRequestId())||result.getCode()==null||!result.getCode().matches("[A-Z0-9_]{1,64}"))throw invalid();return result;
 }
 public static ReservationEvidence map(Reservation r){if(r==null)throw invalid();return new ReservationEvidence(r.getRecordKind(),r.getOrderId(),r.getOutTradeNo(),r.getUserId(),r.getSource(),r.getChannel(),r.getActivityId(),r.getGoodsId(),r.getProductVersion(),r.getQuantity(),r.getTeamId(),r.getOriginalPrice(),r.getDeductionPrice(),r.getPayPrice(),r.getCurrency(),r.getReservedAt(),r.getPaymentDeadline(),r.getOrderStatus(),r.getTeamStatus(),r.getRecordVersion(),r.getTeamVersion(),r.getServerTime(),r.getClosedAt(),r.getPayment()!=null,r.getRefund()!=null);}
 private static OrderFailure invalid(){return new OrderFailure(502,"UPSTREAM_RESPONSE_INVALID");}
 private static String technical(Throwable failure){var seen=java.util.Collections.newSetFromMap(new java.util.IdentityHashMap<Throwable,Boolean>());for(Throwable e=failure;e!=null&&seen.add(e);e=e.getCause()){if(e instanceof org.apache.dubbo.rpc.StatusRpcException s&&(s.getStatus().code==org.apache.dubbo.rpc.TriRpcStatus.Code.UNAUTHENTICATED||s.getStatus().code==org.apache.dubbo.rpc.TriRpcStatus.Code.PERMISSION_DENIED))return "INTEGRATION_AUTH_FAILED";if(e instanceof org.apache.dubbo.rpc.RpcException r&&r.isTimeout())return "UPSTREAM_TIMEOUT";}return "DEPENDENCY_UNAVAILABLE";}
 public void close(){trade.destroy();teams.destroy();}
}
