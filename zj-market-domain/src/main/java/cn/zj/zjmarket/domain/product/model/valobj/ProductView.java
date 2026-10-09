package cn.zj.zjmarket.domain.product.model.valobj;

import cn.zj.zjmarket.domain.product.model.entity.Product;
import java.util.*;
public record ProductView(Product product,ProductSyncProgress sync) {}
