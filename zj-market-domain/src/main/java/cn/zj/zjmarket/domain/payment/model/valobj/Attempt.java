package cn.zj.zjmarket.domain.payment.model.valobj;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
import cn.zj.zjmarket.domain.order.model.valobj.ReservationEvidence;
import cn.zj.zjmarket.types.exception.OrderFailure;
import java.util.*;
public record Attempt(String attemptId,String paymentId,int attemptNo,long version,String state,String amount,long paymentDeadline,Long paidAt,String channelTransactionId,String errorCode){}
