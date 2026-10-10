package cn.zj.zjmarket.infrastructure.adapter.port.order;
import cn.bugstack.api.v2.*;
import cn.zj.zjmarket.domain.order.adapter.port.IPurchaseQuotePort;
import cn.zj.zjmarket.domain.order.model.valobj.PurchaseConditions;
import cn.zj.zjmarket.domain.product.service.IMarketingTrialService;
import cn.zj.zjmarket.infrastructure.config.properties.RpcSettings;
import cn.zj.zjmarket.infrastructure.gateway.codec.ContractCodec;
import cn.zj.zjmarket.infrastructure.gateway.rpc.RpcClientFactory;
import cn.zj.zjmarket.types.exception.OrderFailure;
import org.apache.dubbo.config.ReferenceConfig;
import org.apache.dubbo.rpc.RpcContext;
import java.util.*;
public final class DubboPurchaseQuote implements IPurchaseQuotePort,AutoCloseable {
 private final IMarketingTrialService trial;private final RpcSettings settings;private final ReferenceConfig<TeamService> teams;
 public DubboPurchaseQuote(IMarketingTrialService trial,RpcSettings settings,RpcClientFactory factory){this.trial=trial;this.settings=settings;teams=factory.reference(TeamService.class);teams.setCheck(false);}
 public void verify(String user,PurchaseConditions q,String requestId){
  var result=trial.trial(user,q.goodsId(),requestId);
  if(!"AVAILABLE".equals(result.state()))throw new OrderFailure(409,"OFFER_UNAVAILABLE");
  if(!q.expectedOffer().equals(result.offer()))throw new OrderFailure(409,"OFFER_CHANGED",Map.of("latestOffer",result.offer()));
  if("JOIN".equals(q.mode()))verifyTeam(user,q,requestId);
 }
 private void verifyTeam(String user,PurchaseConditions q,String requestId){
  var request=new TeamQueryRequest();request.setUserId(user);request.setTeamId(q.teamId());request.setSource(settings.getSource());request.setChannel(settings.getChannel());
  byte[] random=new byte[24];new java.security.SecureRandom().nextBytes(random);String nonce=Base64.getUrlEncoder().withoutPadding().encodeToString(random),time=Long.toString(System.currentTimeMillis());
  try {
  String canonical=String.join("\n",settings.getClientId(),settings.getKeyId(),time,nonce,requestId,TeamService.class.getName(),"query",settings.getVersion(),settings.getGroup(),ContractCodec.sha256(new ContractCodec().encode(request)));
  var attachments=Map.of("clientId",settings.getClientId(),"keyId",settings.getKeyId(),"timestamp",time,"nonce",nonce,"requestId",requestId,"signature",ContractCodec.hmac(settings.getSecret(),canonical));
  RpcResult<Team> response;
  try{attachments.forEach((k,v)->RpcContext.getClientAttachment().setAttachment(k,v));response=teams.get().query(request);}catch(Exception e){throw new OrderFailure(503,"DEPENDENCY_UNAVAILABLE");}finally{RpcContext.getClientAttachment().clearAttachments();}
  if(response==null||!requestId.equals(response.getRequestId()))throw new OrderFailure(502,"UPSTREAM_RESPONSE_INVALID");
  if(!"0000".equals(response.getCode())){if(Set.of("AUTH_REQUIRED","AUTH_INVALID","FORBIDDEN","REPLAY_REJECTED").contains(Objects.toString(response.getCode(),"")))throw new OrderFailure(502,"INTEGRATION_AUTH_FAILED");throw new OrderFailure(409,"TEAM_NOT_JOINABLE");}
  var t=response.getData();if(t==null||!q.teamId().equals(t.getTeamId())||!q.goodsId().equals(t.getGoodsId())||!q.expectedOffer().activityId().equals(t.getActivityId())||!settings.getSource().equals(t.getSource())||!settings.getChannel().equals(t.getChannel())||!q.expectedOffer().targetCount().equals(t.getTargetCount())||t.getJoinable()==null)throw new OrderFailure(502,"UPSTREAM_RESPONSE_INVALID");
  if(!t.getJoinable())throw new OrderFailure(409,"TEAM_NOT_JOINABLE");
  }catch(OrderFailure e){throw e;}catch(Exception e){throw new OrderFailure(503,"DEPENDENCY_UNAVAILABLE");}
 }
 public void close(){teams.destroy();}
}
