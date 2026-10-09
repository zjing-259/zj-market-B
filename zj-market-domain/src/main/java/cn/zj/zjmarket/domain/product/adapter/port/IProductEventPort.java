package cn.zj.zjmarket.domain.product.adapter.port;

import cn.zj.zjmarket.domain.product.model.entity.Product;
public interface IProductEventPort { String encode(Product product,String eventId,String correlationId); }
