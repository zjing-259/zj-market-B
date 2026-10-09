package cn.zj.zjmarket.domain.product.model.valobj;

import java.util.*;
public record QuarantinePage(List<QuarantinedMessage> items,int page,int size,long total){}
