package cn.zj.zjmarket.domain.payment.model.valobj;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
import cn.zj.zjmarket.domain.order.model.valobj.ReservationEvidence;
import cn.zj.zjmarket.types.exception.OrderFailure;
import java.util.*;
public record Accepted(Receipt receipt,boolean replay,boolean applied){public Accepted(Receipt receipt,boolean replay){this(receipt,replay,false);}}
