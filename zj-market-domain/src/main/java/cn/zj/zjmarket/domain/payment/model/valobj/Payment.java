package cn.zj.zjmarket.domain.payment.model.valobj;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
import cn.zj.zjmarket.domain.order.model.valobj.ReservationEvidence;
import cn.zj.zjmarket.types.exception.OrderFailure;
import java.util.*;
public record Payment(String paymentId,String orderId,String userId,long version,String fundsState,String gate,String aAcceptance,String amount,String currency,long paymentDeadline,Long paidAt,String activeAttemptId,String successAttemptId,boolean reviewRequired,String errorCode){}
