package cn.zj.zjmarket.domain.product.adapter.repository;

import cn.zj.zjmarket.domain.product.model.valobj.ProductSyncProgress;
import cn.zj.zjmarket.domain.product.model.valobj.QuarantinePage;
import cn.zj.zjmarket.domain.product.model.valobj.SyncBadMessage;
import cn.zj.zjmarket.domain.product.model.valobj.SyncResult;
import cn.zj.zjmarket.domain.product.model.valobj.SyncWork;
import java.util.*;
public interface IProductSyncRepository {


    SyncWork claim(String kind,String eventId,long leaseMillis);
    SyncWork event(String eventId);
    void sent(SyncWork work,long queryMillis);
    void failed(SyncWork work,String kind,String code,boolean permanent,long delayMillis);
    void checked(SyncWork work,String status,long queryMillis);
    void accept(SyncResult result,String consumer);
    ProductSyncProgress progress(String goodsId);
    void control(String goodsId,String eventId,long expected,String operator,boolean pause);


    String quarantine(SyncBadMessage bad);


    QuarantinePage quarantined(int page,int size);
    SyncBadMessage quarantinedBody(String id);
    void replayed(String id);
}
