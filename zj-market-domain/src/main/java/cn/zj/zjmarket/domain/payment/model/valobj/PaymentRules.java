package cn.zj.zjmarket.domain.payment.model.valobj;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
import cn.zj.zjmarket.domain.order.model.valobj.ReservationEvidence;
import cn.zj.zjmarket.types.exception.OrderFailure;
import java.util.*;
public final class PaymentRules {
 private PaymentRules(){}
 public static void id(String s){if(s==null||!s.matches("[A-Za-z0-9][A-Za-z0-9_-]{0,63}"))throw new OrderFailure(400,"VALIDATION_FAILED");}
 public static OrderFailure conflict(String code){return new OrderFailure(409,code);}
}
