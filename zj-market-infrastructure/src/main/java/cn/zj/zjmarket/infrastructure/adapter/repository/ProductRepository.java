package cn.zj.zjmarket.infrastructure.adapter.repository;

import cn.zj.zjmarket.domain.product.adapter.repository.IProductRepository;
import cn.zj.zjmarket.domain.product.model.entity.Product;
import cn.zj.zjmarket.domain.product.model.valobj.ProductFields;
import cn.zj.zjmarket.domain.product.model.valobj.ProductSyncProgress;
import cn.zj.zjmarket.domain.product.model.valobj.SaleStatus;
import cn.zj.zjmarket.infrastructure.dao.IProductDao;
import cn.zj.zjmarket.infrastructure.dao.po.ProductRow;
import java.util.*;
import java.util.function.Supplier;
import org.springframework.transaction.support.TransactionTemplate;
public final class ProductRepository implements IProductRepository {
    private final IProductDao mapper;private final TransactionTemplate tx;
    public ProductRepository(IProductDao mapper,TransactionTemplate tx){this.mapper=mapper;this.tx=tx;}
    public <T>T transaction(Supplier<T> work){return tx.execute(status -> work.get());}
    public Product get(String id,boolean lock){var row=mapper.get(id,lock);return row==null?null:product(row);}
    public ProductSyncProgress progress(String id){return mapper.progress(id);}
    public void insert(Product p){one(mapper.insert(row(p)));}
    public boolean update(Product p,long expected){return mapper.update(row(p),expected)==1;}
    public void appendEvent(Product p,String eventId,String body){one(mapper.append(p.goodsId(),p.version(),eventId,body,p.updatedAt()));}
    public void target(Product p,String eventId){mapper.target(p.goodsId(),p.version(),eventId);}
    public List<Product> list(int page,int size,String status){return mapper.list(((long)page-1)*size,size,status).stream().map(ProductRepository::product).toList();}
    public long count(String status){return mapper.count(status);}
    private static Product product(ProductRow r){return new Product(r.goodsId(),new ProductFields(r.goodsName(),r.description(),r.imageUrl(),r.originalPrice().toPlainString(),r.currency(),SaleStatus.valueOf(r.saleStatus())),r.version(),r.createdAt(),r.updatedAt());}
    private static ProductRow row(Product p){var f=p.fields();return new ProductRow(p.goodsId(),f.goodsName(),f.description(),f.imageUrl(),f.originalPrice(),f.currency(),f.saleStatus().name(),p.version(),p.createdAt(),p.updatedAt());}
    private static void one(int count){if(count!=1)throw new IllegalStateException("Unexpected product write count");}
}
