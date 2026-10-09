package cn.zj.zjmarket.domain.product.adapter.repository;

import cn.zj.zjmarket.domain.product.model.entity.Product;
import cn.zj.zjmarket.domain.product.model.valobj.ProductSyncProgress;
import java.util.*;
import java.util.function.Supplier;
/** Local unit of work: authoritative product, immutable event and sync target commit together. */
public interface IProductRepository {
    <T>T transaction(Supplier<T> work);
    Product get(String id,boolean lock);
    ProductSyncProgress progress(String id);
    void insert(Product product);
    boolean update(Product product,long expectedVersion);
    void appendEvent(Product product,String eventId,String body);
    void target(Product product,String eventId);
    List<Product> list(int page,int size,String status);
    long count(String status);
}
