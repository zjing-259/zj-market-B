package cn.zj.zjmarket.infrastructure.adapter.port.order;

import cn.bugstack.api.v2.*;
import cn.zj.zjmarket.domain.order.adapter.port.ITeamDiscoveryPort;
import cn.zj.zjmarket.domain.order.model.valobj.*;
import cn.zj.zjmarket.infrastructure.config.properties.RpcSettings;
import cn.zj.zjmarket.infrastructure.gateway.codec.ContractCodec;
import cn.zj.zjmarket.infrastructure.gateway.rpc.RpcClientFactory;
import cn.zj.zjmarket.types.exception.ProductFailure;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.*;
import java.nio.ByteBuffer;
import java.nio.charset.*;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.*;
import org.apache.dubbo.config.ReferenceConfig;
import org.apache.dubbo.rpc.RpcContext;

/** Signed read-only discovery call. Transport DTOs are discarded at this boundary. */
public final class DubboTeamDiscoveryPort implements ITeamDiscoveryPort,AutoCloseable {
 private static final ObjectMapper JSON=new ObjectMapper().enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION);
 private final RpcSettings settings;private final ReferenceConfig<TeamDiscoveryService> reference;private final SecureRandom random=new SecureRandom();
 public DubboTeamDiscoveryPort(RpcSettings settings,RpcClientFactory factory){this.settings=settings;reference=factory.reference(TeamDiscoveryService.class);reference.setCheck(false);reference.setTimeout(3000);reference.setRetries(0);}
 public DiscoveryPage list(String user,String goods,String activity,String version,int target,int limit,String cursor,String requestId){
  TeamDiscoveryRequest request=new TeamDiscoveryRequest();request.setSource(settings.getSource());request.setChannel(settings.getChannel());request.setUserId(user);request.setGoodsId(goods);request.setActivityId(activity);request.setProductVersion(version);request.setLimit(limit);request.setCursor(cursor);
  try{
   byte[] nonceBytes=new byte[24];random.nextBytes(nonceBytes);String nonce=Base64.getUrlEncoder().withoutPadding().encodeToString(nonceBytes),time=Long.toString(System.currentTimeMillis());
   String canonical=String.join("\n",settings.getClientId(),settings.getKeyId(),time,nonce,requestId,TeamDiscoveryService.class.getName(),"list",settings.getVersion(),settings.getGroup(),ContractCodec.sha256(new ContractCodec().encode(request)));
   var headers=Map.of("clientId",settings.getClientId(),"keyId",settings.getKeyId(),"timestamp",time,"nonce",nonce,"requestId",requestId,"signature",ContractCodec.hmac(settings.getSecret(),canonical));
   RpcResult<TeamDiscoveryPage> response;
   try{headers.forEach((k,v)->RpcContext.getClientAttachment().setAttachment(k,v));response=reference.get().list(request);}finally{RpcContext.getClientAttachment().clearAttachments();}
   return readResponse(response,request,requestId,target);
  }catch(ProductFailure e){throw e;}catch(Exception e){throw transport(e);}
 }
 public static DiscoveryPage readResponse(RpcResult<TeamDiscoveryPage> response,TeamDiscoveryRequest request,String requestId,int target){
  if(response==null||!requestId.equals(response.getRequestId())||response.getCode()==null)throw invalid();
  if(!"0000".equals(response.getCode())){
   if(response.getData()!=null)throw invalid();
   String code=response.getCode();
   if(Set.of("AUTH_REQUIRED","AUTH_INVALID","FORBIDDEN","REPLAY_REJECTED","E0112").contains(code))throw failure(502,"INTEGRATION_AUTH_FAILED");
   if("0002".equals(code))throw failure(400,"VALIDATION_FAILED");
   if(Set.of("TEAM_DISCOVERY_CONTEXT_CHANGED","PRODUCT_VERSION_MISMATCH","PRODUCT_VERSION_CONFLICT","PRODUCT_NOT_SALEABLE").contains(code))throw failure(409,"TEAM_DISCOVERY_CONTEXT_CHANGED");
   if("PRODUCT_NOT_FOUND".equals(code))return DiscoveryPage.unavailable("PRODUCT_SYNC_PENDING",request.getGoodsId(),request.getProductVersion());
   if(Set.of("E0101","E0102","E0108").contains(code)){if(request.getCursor()!=null)throw failure(409,"TEAM_DISCOVERY_CONTEXT_CHANGED");return DiscoveryPage.unavailable("NO_OFFER",request.getGoodsId(),request.getProductVersion());}
   if("E0110".equals(code))return DiscoveryPage.unavailable("INELIGIBLE",request.getGoodsId(),request.getProductVersion());
   if(Set.of("0001","DEPENDENCY_UNAVAILABLE","E0003","E0004","E0105").contains(code))throw failure(503,"DEPENDENCY_UNAVAILABLE");
   throw invalid();
  }
  TeamDiscoveryPage p=response.getData();
  if(p==null||!Objects.equals(p.getSource(),request.getSource())||!Objects.equals(p.getChannel(),request.getChannel())||!Objects.equals(p.getUserId(),request.getUserId())||!Objects.equals(p.getGoodsId(),request.getGoodsId())||!Objects.equals(p.getActivityId(),request.getActivityId())||!Objects.equals(p.getProductVersion(),request.getProductVersion())||p.getItems()==null||p.getHasMore()==null||p.getItems().size()>request.getLimit()||!time(p.getServerTime()))throw invalid();
  String lastTime=null,lastId=null;HashSet<String> seen=new HashSet<>();List<DiscoveryItem> items=new ArrayList<>();
  for(TeamDiscoveryItem t:p.getItems()){
   if(t==null||!id(t.getTeamId())||!Objects.equals(t.getGoodsId(),request.getGoodsId())||!Objects.equals(t.getActivityId(),request.getActivityId())||!version(t.getTeamVersion())||!"FORMING".equals(t.getTeamStatus())||t.getTargetCount()==null||t.getTargetCount()!=target||target<1||target>100||t.getReservedCount()==null||t.getPaidCount()==null||t.getPaidCount()<1||t.getPaidCount()>t.getReservedCount()||t.getReservedCount()>=target||!time(t.getValidStartTime())||!time(t.getValidEndTime())||t.getValidStartTime().compareTo(p.getServerTime())>0||t.getValidEndTime().compareTo(p.getServerTime())<=0||!seen.add(t.getTeamId())||lastTime!=null&&(t.getValidEndTime().compareTo(lastTime)<0||t.getValidEndTime().equals(lastTime)&&compareUtf8(t.getTeamId(),lastId)<=0))throw invalid();
   lastTime=t.getValidEndTime();lastId=t.getTeamId();items.add(new DiscoveryItem(t.getTeamId(),target,t.getReservedCount(),t.getPaidCount(),target-t.getReservedCount(),target-t.getPaidCount(),t.getValidEndTime()));
  }
  if(p.getHasMore()!=(p.getNextCursor()!=null)||p.getHasMore()&&items.size()!=request.getLimit()||items.isEmpty()&&p.getNextCursor()!=null)throw invalid();
  if(p.getNextCursor()!=null)cursor(p.getNextCursor(),request,lastTime,lastId);
  return new DiscoveryPage("AVAILABLE",null,request.getGoodsId(),request.getProductVersion(),request.getActivityId(),p.getServerTime(),List.copyOf(items),null,p.getNextCursor(),p.getHasMore());
 }
 public void validateCursor(String user,String goods,String encoded){
  if(encoded==null)return;
  try{
   JsonNode n=decodeCursor(encoded);
   if(n.size()!=10||!n.path("cursorVersion").isIntegralNumber()||n.path("cursorVersion").intValue()!=1||!"END_TEAM_ASC_V1".equals(n.path("sortVersion").textValue())||!time(n.path("lastEndTime").textValue())||!id(n.path("lastTeamId").textValue())||!version(n.path("productVersion").textValue())||!version(n.path("activityId").textValue()))throw new ProductFailure(400,"VALIDATION_FAILED");
   if(!Objects.equals(n.path("source").textValue(),settings.getSource())||!Objects.equals(n.path("channel").textValue(),settings.getChannel())||!Objects.equals(n.path("userId").textValue(),user))throw new ProductFailure(400,"VALIDATION_FAILED");
   if(!Objects.equals(n.path("goodsId").textValue(),goods))throw new ProductFailure(409,"TEAM_DISCOVERY_CONTEXT_CHANGED");
  }catch(ProductFailure e){if(e.status()==502)throw new ProductFailure(400,"VALIDATION_FAILED");throw e;}
 }
 private static void cursor(String encoded,TeamDiscoveryRequest r,String lastTime,String lastId){
  JsonNode n=decodeCursor(encoded);
  if(n.size()!=10||!n.path("cursorVersion").isIntegralNumber()||n.path("cursorVersion").intValue()!=1||!"END_TEAM_ASC_V1".equals(n.path("sortVersion").asText())||!Objects.equals(n.path("source").textValue(),r.getSource())||!Objects.equals(n.path("channel").textValue(),r.getChannel())||!Objects.equals(n.path("userId").textValue(),r.getUserId())||!Objects.equals(n.path("goodsId").textValue(),r.getGoodsId())||!Objects.equals(n.path("activityId").textValue(),r.getActivityId())||!Objects.equals(n.path("productVersion").textValue(),r.getProductVersion())||!Objects.equals(n.path("lastEndTime").textValue(),lastTime)||!Objects.equals(n.path("lastTeamId").textValue(),lastId))throw invalid();
 }
 private static JsonNode decodeCursor(String encoded){
  try{
   if(encoded.isEmpty()||encoded.length()>1024||!encoded.matches("[A-Za-z0-9_-]+"))throw invalid();
   byte[] bytes=Base64.getUrlDecoder().decode(encoded);if(bytes.length>768||!Base64.getUrlEncoder().withoutPadding().encodeToString(bytes).equals(encoded))throw invalid();
   String raw=StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
   JsonNode n=JSON.readTree(raw);if(n==null||!n.isObject()||!raw.equals(JSON.writeValueAsString(n)))throw invalid();
   List<String> fields=new ArrayList<>();n.fieldNames().forEachRemaining(fields::add);
   if(!fields.equals(List.of("activityId","channel","cursorVersion","goodsId","lastEndTime","lastTeamId","productVersion","sortVersion","source","userId")))throw invalid();
   return n;
  }catch(ProductFailure e){throw e;}catch(Exception e){throw invalid();}
 }
 private static boolean id(String s){return s!=null&&!s.isEmpty()&&s.length()<=64&&s.equals(s.trim())&&s.indexOf('\r')<0&&s.indexOf('\n')<0&&!Character.isWhitespace(s.codePointAt(0))&&!Character.isSpaceChar(s.codePointAt(0))&&!Character.isWhitespace(s.codePointBefore(s.length()))&&!Character.isSpaceChar(s.codePointBefore(s.length()));}
 private static int compareUtf8(String a,String b){byte[] left=a.getBytes(StandardCharsets.UTF_8),right=b.getBytes(StandardCharsets.UTF_8);for(int i=0;i<Math.min(left.length,right.length);i++){int d=Byte.toUnsignedInt(left[i])-Byte.toUnsignedInt(right[i]);if(d!=0)return d;}return Integer.compare(left.length,right.length);}
 private static boolean version(String s){if(s==null||!s.matches("[1-9][0-9]{0,18}"))return false;try{return Long.parseLong(s)>0;}catch(NumberFormatException e){return false;}}
 private static boolean time(String s){try{return s!=null&&s.matches("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{3}Z")&&Instant.parse(s)!=null;}catch(Exception e){return false;}}
 private static ProductFailure invalid(){return failure(502,"UPSTREAM_RESPONSE_INVALID");}
 private static ProductFailure failure(int status,String code){return new ProductFailure(status,code);}
 public static ProductFailure transport(Throwable error){Set<Throwable> seen=Collections.newSetFromMap(new IdentityHashMap<>());for(Throwable cause=error;cause!=null&&seen.add(cause);cause=cause.getCause()){
  if(cause instanceof javax.net.ssl.SSLException||cause instanceof java.security.cert.CertificateException)return failure(502,"INTEGRATION_AUTH_FAILED");
  if(cause instanceof org.apache.dubbo.rpc.StatusRpcException status&&(status.getStatus().code==org.apache.dubbo.rpc.TriRpcStatus.Code.UNAUTHENTICATED||status.getStatus().code==org.apache.dubbo.rpc.TriRpcStatus.Code.PERMISSION_DENIED))return failure(502,"INTEGRATION_AUTH_FAILED");
 }return failure(503,"DEPENDENCY_UNAVAILABLE");}
 public void close(){reference.destroy();}
}
