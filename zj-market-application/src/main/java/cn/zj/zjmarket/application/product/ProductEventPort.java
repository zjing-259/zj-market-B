package cn.zj.zjmarket.application.product;
import cn.zj.zjmarket.domain.product.Product;
public interface ProductEventPort { String encode(Product product,String eventId,String correlationId); }
