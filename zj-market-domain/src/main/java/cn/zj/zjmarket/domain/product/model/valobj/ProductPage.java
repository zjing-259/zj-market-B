package cn.zj.zjmarket.domain.product.model.valobj;

import java.util.*;
public record ProductPage(List<ProductView> items,int page,int size,long total) {}
