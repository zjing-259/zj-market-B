package cn.zj.zjmarket.domain.payment.model.valobj;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
import cn.zj.zjmarket.domain.order.model.valobj.ReservationEvidence;
import java.util.Objects;
/** Full A payment evidence must match this order's immutable local money. */
public record CompletionEvidence(String orderId,String outTradeNo,String teamId,String orderStatus,String teamStatus,String recordVersion,String teamVersion,String paymentId,String amount,String currency,String paidAt) {
 public void validate(MarketOrder o,Payment p){var a=o.evidence();if(a==null||!Objects.equals(orderId,a.orderId())||!Objects.equals(outTradeNo,o.orderId())||!Objects.equals(teamId,a.teamId())||!"PAID".equals(orderStatus)||!Objects.equals(paymentId,p.paymentId())||!Objects.equals(amount,p.amount())||!Objects.equals(currency,p.currency())||p.paidAt()==null||ReservationEvidence.instant(paidAt)!=p.paidAt()||!"SUCCEEDED".equals(p.fundsState())||!"ACCEPTED".equals(p.aAcceptance()))throw new IllegalArgumentException("Completion payment mismatch");ReservationEvidence.version(recordVersion);ReservationEvidence.version(teamVersion);}
}
