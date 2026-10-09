package cn.zj.zjmarket.domain.product.service;

import cn.zj.zjmarket.domain.product.model.valobj.ProductFields;
import cn.zj.zjmarket.domain.product.model.valobj.ProductPage;
import cn.zj.zjmarket.domain.product.model.valobj.ProductView;
public interface IProductService {
 ProductView create(ProductFields fields,String correlationId);
 ProductView edit(String id,long expected,ProductFields fields,String correlationId);
 ProductView detail(String id,boolean admin);
 ProductPage list(int page,int size,String status,boolean admin);
}
