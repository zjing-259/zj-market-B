package cn.zj.zjmarket.infrastructure.dao.po;

import java.math.BigDecimal;
import org.apache.ibatis.annotations.*;
public record ProductRow(String goodsId,String goodsName,String description,String imageUrl,BigDecimal originalPrice,String currency,String saleStatus,long version,long createdAt,long updatedAt){}
