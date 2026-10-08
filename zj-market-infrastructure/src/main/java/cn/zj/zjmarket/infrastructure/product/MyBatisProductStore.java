package cn.zj.zjmarket.infrastructure.product;
import cn.zj.zjmarket.application.product.*;
import cn.zj.zjmarket.domain.product.*;
import org.springframework.transaction.support.TransactionTemplate;
import java.math.BigDecimal;
import java.util.*;
import java.util.function.Supplier;
public final class MyBatisProductStore implements ProductStore {
    private final ProductMapper mapper;private final TransactionTemplate tx;
    public MyBatisProductStore(ProductMapper mapper,TransactionTemplate tx){this.mapper=mapper;this.tx=tx;}
    public <T>T transaction(Supplier<T> work){return tx.execute(status -> work.get());}
    public Product get(String id,boolean lock){var row=mapper.get(id,lock);return row==null?null:product(row);}
    public ProductSyncProgress progress(String id){return mapper.progress(id);}
    public void insert(Product p){one(mapper.insert(row(p)));}
    public boolean update(Product p,long expected){return mapper.update(row(p),expected)==1;}
    public void appendEvent(Product p,String eventId,String body){one(mapper.append(p.goodsId(),p.version(),eventId,body,p.updatedAt()));}
    public void target(Product p,String eventId){mapper.target(p.goodsId(),p.version(),eventId);}
    public List<Product> list(int page,int size,String status){return mapper.list(((long)page-1)*size,size,status).stream().map(MyBatisProductStore::product).toList();}
    public long count(String status){return mapper.count(status);}
    private static Product product(ProductMapper.Row r){return new Product(r.goodsId(),new Product.Fields(r.goodsName(),r.description(),r.imageUrl(),r.originalPrice().toPlainString(),r.currency(),Product.SaleStatus.valueOf(r.saleStatus())),r.version(),r.createdAt(),r.updatedAt());}
    private static ProductMapper.Row row(Product p){var f=p.fields();return new ProductMapper.Row(p.goodsId(),f.goodsName(),f.description(),f.imageUrl(),f.originalPrice(),f.currency(),f.saleStatus().name(),p.version(),p.createdAt(),p.updatedAt());}
    private static void one(int count){if(count!=1)throw new IllegalStateException("Unexpected product write count");}
}
