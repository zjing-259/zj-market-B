package cn.zj.zjmarket.infrastructure.product;
import cn.zj.zjmarket.application.product.*;
import cn.zj.zjmarket.domain.product.Product;
import cn.zj.zjmarket.infrastructure.config.RpcSettings;
import cn.zj.zjmarket.infrastructure.integration.rpc.RpcClientFactory;
import cn.zj.zjmarket.infrastructure.integration.codec.ContractCodec;
import cn.bugstack.api.v2.*;
import org.apache.dubbo.config.ReferenceConfig;
import org.apache.dubbo.rpc.RpcContext;
import org.apache.dubbo.rpc.RpcException;
import java.security.SecureRandom;
import java.util.*;
/** TLS, fresh signed attachments and no automatic RPC retry; initializes lazily when a user requests a quote. */
public final class DubboMarketingTrial implements MarketingTrialPort,AutoCloseable {
    private final RpcSettings rpc;private final ReferenceConfig<MarketingService> reference;
    public DubboMarketingTrial(RpcSettings rpc,RpcClientFactory factory){this.rpc=rpc;reference=factory.reference(MarketingService.class);reference.setCheck(false);}
    public Quote trial(String userId,Product product,String requestId){
        try{
            var request=new TrialRequest();request.setUserId(userId);request.setGoodsId(product.goodsId());request.setQuantity(1);request.setProductVersion(Long.toString(product.version()));request.setSource(rpc.getSource());request.setChannel(rpc.getChannel());request.setActivityId(null);
            byte[] random=new byte[24];new SecureRandom().nextBytes(random);String timestamp=Long.toString(System.currentTimeMillis()),nonce=Base64.getUrlEncoder().withoutPadding().encodeToString(random);
            String canonical=String.join("\n",rpc.getClientId(),rpc.getKeyId(),timestamp,nonce,requestId,MarketingService.class.getName(),"trial",rpc.getVersion(),rpc.getGroup(),ContractCodec.sha256(new ContractCodec().encode(request)));
            var attachments=Map.of("clientId",rpc.getClientId(),"keyId",rpc.getKeyId(),"timestamp",timestamp,"nonce",nonce,"requestId",requestId,"signature",ContractCodec.hmac(rpc.getSecret(),canonical));
            RpcResult<TrialResponse> response;
            try{attachments.forEach((key,value)->RpcContext.getClientAttachment().setAttachment(key,value));response=reference.get().trial(request);}finally{RpcContext.getClientAttachment().clearAttachments();}
            return readResponse(response,requestId);
        }catch(ProductFailure failure){throw failure;}
        catch(Exception failure){throw networkFailure(failure);}
    }
    private static ProductFailure networkFailure(Throwable failure){
        Set<Throwable> seen=Collections.newSetFromMap(new IdentityHashMap<>());
        for(Throwable cause=failure;cause!=null && seen.add(cause);cause=cause.getCause()){
            if(cause instanceof RpcException rpcFailure && rpcFailure.isTimeout()
                || cause instanceof org.apache.dubbo.rpc.StatusRpcException status && status.getStatus().code==org.apache.dubbo.rpc.TriRpcStatus.Code.DEADLINE_EXCEEDED
                || cause instanceof java.util.concurrent.TimeoutException
                || cause instanceof org.apache.dubbo.remoting.TimeoutException)return new ProductFailure(504,"UPSTREAM_TIMEOUT");
        }
        return new ProductFailure(503,"DEPENDENCY_UNAVAILABLE");
    }
    /** Validates the typed RPC envelope before any offer can enter the application. */
    public static Quote readResponse(RpcResult<TrialResponse> response,String requestId){
            if(response==null || !requestId.equals(response.getRequestId()))throw new ProductFailure(502,"UPSTREAM_RESPONSE_INVALID");
            if(!"0000".equals(response.getCode()))throw error(response.getCode());
            var q=response.getData();if(q==null || q.getAvailable()==null || q.getVisible()==null || q.getEligible()==null)throw new ProductFailure(502,"UPSTREAM_RESPONSE_INVALID");
            // Hidden offers are discarded before mapping: no activity identifier, raw reason or price leaks out of infrastructure.
            cn.bugstack.api.v2.Offer o=q.getAvailable() && q.getVisible()?q.getOffer():null;
            return new Quote(q.getAvailable(),q.getVisible(),q.getEligible(),q.getQuotedAt(),o==null?null:new MarketingTrialPort.Offer(o.getActivityId(),o.getGoodsId(),o.getProductVersion(),o.getOriginalPrice(),o.getDeductionPrice(),o.getPayPrice(),o.getCurrency(),o.getTargetCount()));
    }
    private static ProductFailure error(String code){
        if(Set.of("AUTH_REQUIRED","AUTH_INVALID","FORBIDDEN","REPLAY_REJECTED","E0112").contains(Objects.toString(code,"")))return new ProductFailure(502,"INTEGRATION_AUTH_FAILED");
        if(Set.of("PRODUCT_VERSION_MISMATCH","PRODUCT_NOT_SALEABLE").contains(Objects.toString(code,"")))return new ProductFailure(409,"PRODUCT_VERSION_MISMATCH");
        if("PRODUCT_NOT_FOUND".equals(code))return new ProductFailure(409,"PRODUCT_SYNC_PENDING");
        return new ProductFailure(503,"DEPENDENCY_UNAVAILABLE");
    }
    public void close(){reference.destroy();}
}
