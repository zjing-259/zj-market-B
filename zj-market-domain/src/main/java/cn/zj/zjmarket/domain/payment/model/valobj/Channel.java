package cn.zj.zjmarket.domain.payment.model.valobj;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
import cn.zj.zjmarket.domain.order.model.valobj.ReservationEvidence;
import cn.zj.zjmarket.types.exception.OrderFailure;
import java.util.*;
public record Channel(String paymentId,String attemptId,String state,String channelTransactionId,String amount,String currency,Long paidAt){}
