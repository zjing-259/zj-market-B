package cn.zj.zjmarket.domain.product.service;

import cn.zj.zjmarket.domain.product.model.valobj.ProductSyncProgress;
import cn.zj.zjmarket.domain.product.model.valobj.QuarantinePage;
import cn.zj.zjmarket.domain.product.model.valobj.SyncResult;
public interface IProductSyncService {
 boolean publishOne(String eventId);
 boolean queryOne(String eventId);
 void accept(SyncResult result);
 ProductSyncProgress progress(String id);
 void pause(String id,String eventId,long expected,String operator);
 void retry(String id,String eventId,long expected,String operator);
 QuarantinePage quarantined(int page,int size);
}
