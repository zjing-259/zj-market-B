package cn.zj.zjmarket.application.product;
import cn.zj.zjmarket.domain.product.*;
import java.util.*;
/** Network operations occur outside the store's short local transactions. */
public final class ProductSyncService {
    private final SyncStore store;private final SyncTransport transport;private final long leaseMillis,queryMillis,baseRetry,maxRetry;
    public ProductSyncService(SyncStore store,SyncTransport transport,long leaseMillis,long queryMillis,long baseRetry,long maxRetry){this.store=store;this.transport=transport;this.leaseMillis=leaseMillis;this.queryMillis=queryMillis;this.baseRetry=baseRetry;this.maxRetry=maxRetry;}
    public boolean publishOne(String eventId){
        var w=store.claim("SEND",eventId,leaseMillis);if(w==null)return false;
        try{transport.publish(w);store.sent(w,queryMillis);}
        catch(SyncTransport.Failure e){store.failed(w,"SEND",e.code(),e.permanent(),backoff(w.sendFailures()));if(!e.permanent() && w.sendFailures()+1==5)System.err.println("B product sync alert: five consecutive publish failures; original event retained for recovery: "+w.eventId());}
        return true;
    }
    public boolean queryOne(String eventId){
        var w=store.claim("QUERY",eventId,leaseMillis);if(w==null)return false;
        try{var result=transport.query(w);if(result.status().equals("PROCESSED"))store.accept(result.result(),"PRODUCT_SYNC_RPC");else store.checked(w,result.status(),queryMillis);}
        catch(SyncTransport.Failure e){store.failed(w,"QUERY",e.code(),e.permanent(),queryMillis);}
        return true;
    }
    private long backoff(int failures){long delay=Math.min(maxRetry,baseRetry*(1L<<Math.min(20,failures)));return delay;}
    public void accept(SyncTransport.Result result){store.accept(result,"PRODUCT_SYNC_MQ");}
    public ProductSyncProgress progress(String id){return store.progress(id);}
    public void pause(String id,String eventId,long expected,String operator){store.control(id,eventId,expected,operator,true);}
    public void retry(String id,String eventId,long expected,String operator){
        var w=store.event(eventId);if(w==null || !w.goodsId().equals(id) || w.version()!=expected)throw new ProductFailure(409,"RETRY_NOT_ALLOWED");
        var progress=store.progress(id);
        if(!progress.targetEventId().equals(eventId) || !progress.targetVersion().equals(Long.toString(expected)) || Set.of("CONFIRMED","REJECTED").contains(w.processingState()) || Set.of("RESULT_VERSION_MISMATCH","RESULT_CONFLICT","INBOX_BODY_CONFLICT","LOCAL_FACT_INVALID").contains(progress.lastError()==null?"":progress.lastError()))throw new ProductFailure(409,"RETRY_NOT_ALLOWED");
        // Published facts require a fresh authoritative NOT_FOUND before controlled re-publication.
        if(w.deliveryState().equals("PUBLISHED")){
            var query=transport.query(w);if(query.status().equals("PROCESSED")){store.accept(query.result(),"PRODUCT_SYNC_RPC");throw new ProductFailure(409,"RETRY_NOT_ALLOWED");}
            if(!query.status().equals("NOT_FOUND"))throw new ProductFailure(409,"RETRY_NOT_ALLOWED");
        }
        store.control(id,eventId,expected,operator,false);
    }
    public SyncStore.Page quarantined(int page,int size){if(page<1 || size<1 || size>100)throw new ProductFailure(400,"VALIDATION_FAILED");return store.quarantined(page,size);}
}
