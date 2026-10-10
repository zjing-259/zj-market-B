package cn.zj.zjmarket.domain.order.model.valobj;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
public record OrderWrite(MarketOrder order,boolean replay) {}
