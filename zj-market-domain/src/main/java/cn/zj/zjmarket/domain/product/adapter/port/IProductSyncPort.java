package cn.zj.zjmarket.domain.product.adapter.port;

import cn.zj.zjmarket.domain.product.model.valobj.SyncQuery;
import cn.zj.zjmarket.domain.product.model.valobj.SyncWork;
/** SDK-free integration port. Raw immutable fact bytes are never rebuilt for retries. */
public interface IProductSyncPort {
    void publish(SyncWork work);
    SyncQuery query(SyncWork work);


}
