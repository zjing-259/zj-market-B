package cn.zj.zjmarket.application.product;
import cn.zj.zjmarket.domain.product.*;
import java.time.Clock;
import java.util.*;
public final class ProductService {
    private final ProductStore store;private final ProductEventPort events;private final Clock clock;
    public ProductService(ProductStore store,ProductEventPort events,Clock clock){this.store=store;this.events=events;this.clock=clock;}
    public record View(Product product,ProductSyncProgress sync) {}
    public record Page(List<View> items,int page,int size,long total) {}
    public View create(Product.Fields fields,String correlationId){return store.transaction(() -> {
        long now=clock.millis();var product=new Product(UUID.randomUUID().toString(),fields,1,now,now);
        store.insert(product);saveFact(product,correlationId);return view(product);
    });}
    public View edit(String id,long expected,Product.Fields fields,String correlationId){return store.transaction(() -> {
        var before=require(id,true,false);if(before.version()!=expected)throw new ProductFailure(409,"PRODUCT_EDIT_CONFLICT");
        final Product after;try{after=before.edit(fields,clock.millis());}catch(ArithmeticException e){throw new ProductFailure(409,"PRODUCT_VERSION_EXHAUSTED");}
        if(after==before)return view(before);
        if(!store.update(after,expected))throw new ProductFailure(409,"PRODUCT_EDIT_CONFLICT");
        saveFact(after,correlationId);return view(after);
    });}
    public View detail(String id,boolean admin){return store.transaction(() -> view(require(id,false,!admin)));}
    public Page list(int page,int size,String status,boolean admin){
        if(page<1 || size<1 || size>100 || status!=null && !Set.of("ON_SALE","OFF_SALE").contains(status))throw new ProductFailure(400,"VALIDATION_FAILED");
        String filter=admin?status:"ON_SALE";
        return store.transaction(() -> new Page(store.list(page,size,filter).stream().map(this::view).toList(),page,size,store.count(filter)));
    }
    private Product require(String id,boolean lock,boolean publicOnly){
        if(id==null || !id.matches("[A-Za-z0-9._-]{1,64}"))throw new ProductFailure(404,"PRODUCT_NOT_FOUND");
        var p=store.get(id,lock);if(p==null || publicOnly && p.fields().saleStatus()!=Product.SaleStatus.ON_SALE)throw new ProductFailure(404,"PRODUCT_NOT_FOUND");return p;
    }
    private View view(Product p){var sync=store.progress(p.goodsId());if(sync==null || !Long.toString(p.version()).equals(sync.targetVersion()))throw new IllegalStateException("Product sync target missing");return new View(p,sync);}
    private void saveFact(Product p,String correlationId){String eventId=UUID.randomUUID().toString();String body=events.encode(p,eventId,correlationId);store.appendEvent(p,eventId,body);store.target(p,eventId);}
}
