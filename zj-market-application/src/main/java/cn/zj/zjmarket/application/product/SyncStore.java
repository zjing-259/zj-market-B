package cn.zj.zjmarket.application.product;
import cn.zj.zjmarket.domain.product.ProductSyncProgress;
import java.util.*;
public interface SyncStore {
    record Work(String eventId,String goodsId,long version,String saleStatus,String body,String bodyHash,String deliveryState,int sendAttempts,int sendFailures,int queryAttempts,String leaseToken,String processingState,boolean paused){}
    Work claim(String kind,String eventId,long leaseMillis);
    Work event(String eventId);
    void sent(Work work,long queryMillis);
    void failed(Work work,String kind,String code,boolean permanent,long delayMillis);
    void checked(Work work,String status,long queryMillis);
    void accept(SyncTransport.Result result,String consumer);
    ProductSyncProgress progress(String goodsId);
    void control(String goodsId,String eventId,long expected,String operator,boolean pause);
    record BadMessage(String topic,String tag,String keyId,String signature,byte[] body,String reason){}
    String quarantine(BadMessage bad);
    record Quarantined(String quarantineId,String bodyHash,String reason,int originalSize,long storedAt,String state){}
    record Page(List<Quarantined> items,int page,int size,long total){}
    Page quarantined(int page,int size);
    BadMessage quarantinedBody(String id);
    void replayed(String id);
}
