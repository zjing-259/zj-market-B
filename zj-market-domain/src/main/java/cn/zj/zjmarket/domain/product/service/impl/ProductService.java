package cn.zj.zjmarket.domain.product.service.impl;

import cn.zj.zjmarket.domain.product.adapter.port.IProductEventPort;
import cn.zj.zjmarket.domain.product.adapter.repository.IProductRepository;
import cn.zj.zjmarket.domain.product.model.entity.Product;
import cn.zj.zjmarket.domain.product.model.valobj.ProductFields;
import cn.zj.zjmarket.domain.product.model.valobj.ProductPage;
import cn.zj.zjmarket.domain.product.model.valobj.ProductView;
import cn.zj.zjmarket.domain.product.model.valobj.SaleStatus;
import cn.zj.zjmarket.domain.product.service.IProductService;
import cn.zj.zjmarket.types.exception.ProductFailure;
import java.time.Clock;
import java.util.*;
public final class ProductService implements IProductService {
    private final IProductRepository store;private final IProductEventPort events;private final Clock clock;
    public ProductService(IProductRepository store,IProductEventPort events,Clock clock){this.store=store;this.events=events;this.clock=clock;}


    public ProductView create(ProductFields fields,String correlationId){return store.transaction(() -> {
        long now=clock.millis();var product=new Product(UUID.randomUUID().toString(),fields,1,now,now);
        store.insert(product);saveFact(product,correlationId);return view(product);
    });}
    public ProductView edit(String id,long expected,ProductFields fields,String correlationId){return store.transaction(() -> {
        var before=require(id,true,false);if(before.version()!=expected)throw new ProductFailure(409,"PRODUCT_EDIT_CONFLICT");
        final Product after;try{after=before.edit(fields,clock.millis());}catch(ArithmeticException e){throw new ProductFailure(409,"PRODUCT_VERSION_EXHAUSTED");}
        if(after==before)return view(before);
        if(!store.update(after,expected))throw new ProductFailure(409,"PRODUCT_EDIT_CONFLICT");
        saveFact(after,correlationId);return view(after);
    });}
    public ProductView detail(String id,boolean admin){return store.transaction(() -> view(require(id,false,!admin)));}
    public ProductPage list(int page,int size,String status,boolean admin){
        if(page<1 || size<1 || size>100 || status!=null && !Set.of("ON_SALE","OFF_SALE").contains(status))throw new ProductFailure(400,"VALIDATION_FAILED");
        String filter=admin?status:"ON_SALE";
        return store.transaction(() -> new ProductPage(store.list(page,size,filter).stream().map(this::view).toList(),page,size,store.count(filter)));
    }
    private Product require(String id,boolean lock,boolean publicOnly){
        if(id==null || !id.matches("[A-Za-z0-9._-]{1,64}"))throw new ProductFailure(404,"PRODUCT_NOT_FOUND");
        var p=store.get(id,lock);if(p==null || publicOnly && p.fields().saleStatus()!=SaleStatus.ON_SALE)throw new ProductFailure(404,"PRODUCT_NOT_FOUND");return p;
    }
    private ProductView view(Product p){var sync=store.progress(p.goodsId());if(sync==null || !Long.toString(p.version()).equals(sync.targetVersion()))throw new IllegalStateException("Product sync target missing");return new ProductView(p,sync);}
    private void saveFact(Product p,String correlationId){String eventId=UUID.randomUUID().toString();String body=events.encode(p,eventId,correlationId);store.appendEvent(p,eventId,body);store.target(p,eventId);}
}
