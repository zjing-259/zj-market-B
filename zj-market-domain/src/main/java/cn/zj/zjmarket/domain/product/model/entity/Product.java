package cn.zj.zjmarket.domain.product.model.entity;

import cn.zj.zjmarket.domain.product.model.valobj.ProductFields;
/** B's authoritative single-SKU fact. All effective edits share one version. */
public record Product(String goodsId, ProductFields fields, long version, long createdAt, long updatedAt) {


    public Product {
        if(goodsId==null || !goodsId.matches("[A-Za-z0-9._-]{1,64}") || version<1 || fields==null)throw new IllegalArgumentException("Invalid product");
    }
    public Product edit(ProductFields next,long now){if(fields.equals(next))return this;if(version==Long.MAX_VALUE)throw new ArithmeticException("Product version exhausted");return new Product(goodsId,next,version+1,createdAt,now);}
    public static long parseVersion(String value){
        if(value==null || !value.matches("[1-9][0-9]{0,18}"))throw new IllegalArgumentException("Invalid version");
        try{return Long.parseLong(value);}catch(NumberFormatException e){throw new IllegalArgumentException("Invalid version");}
    }
}
