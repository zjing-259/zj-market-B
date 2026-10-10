package cn.zj.zjmarket.domain.order.adapter.port;
import cn.zj.zjmarket.domain.order.model.valobj.PurchaseConditions;
public interface IPurchaseQuotePort { void verify(String userId,PurchaseConditions conditions,String requestId); }
