package cn.zj.zjmarket.domain.order.model.valobj;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
import java.util.*;
import java.time.Instant;
/** A result without transport or SDK types. Versions are parsed exactly, never narrowed. */
public record ReservationEvidence(String recordKind,String orderId,String outTradeNo,String userId,String source,String channel,String activityId,String goodsId,String productVersion,Integer quantity,String teamId,String originalPrice,String deductionPrice,String payPrice,String currency,String reservedAt,String paymentDeadline,String orderStatus,String teamStatus,String recordVersion,String teamVersion,String serverTime,String closedAt,boolean paymentPresent,boolean refundPresent) {
 public void validate(MarketOrder order){
  var c=order.confirmation();var q=c.conditions();var o=q.expectedOffer();
  check(Objects.equals(outTradeNo,order.orderId())&&Objects.equals(userId,c.userId())&&Objects.equals(source,c.source())&&Objects.equals(channel,c.channel()));
  version(recordVersion);instant(serverTime);
  if("CLOSE_MARKER".equals(recordKind)){
   check("CANCELLED".equals(orderStatus));check(instant(closedAt)<=instant(serverTime));
   check(orderId==null&&teamId==null&&goodsId==null&&activityId==null&&productVersion==null&&quantity==null&&originalPrice==null&&deductionPrice==null&&payPrice==null&&currency==null&&reservedAt==null&&paymentDeadline==null&&teamStatus==null&&teamVersion==null&&!paymentPresent&&!refundPresent);var prior=order.evidence();if(prior!=null){check("CLOSE_MARKER".equals(prior.recordKind));if(version(prior.recordVersion)==version(recordVersion))check(Objects.equals(prior.closedAt,closedAt));}return;
  }
  check("RESERVATION".equals(recordKind));id(orderId);id(teamId);version(productVersion);version(activityId);version(teamVersion);
  check(Objects.equals(goodsId,q.goodsId())&&Objects.equals(activityId,o.activityId())&&Objects.equals(productVersion,o.productVersion())&&Objects.equals(quantity,1)&&Objects.equals(originalPrice,o.originalPrice())&&Objects.equals(deductionPrice,o.deductionPrice())&&Objects.equals(payPrice,o.payPrice())&&Objects.equals(currency,"CNY"));
  check(!"JOIN".equals(q.mode())||Objects.equals(teamId,q.teamId()));
  check(Set.of("RESERVED","PAID","CANCELLED").contains(Objects.toString(orderStatus,""))&&Set.of("FORMING","RECONCILING","COMPLETED","FAILED").contains(Objects.toString(teamStatus,"")));
  check(instant(paymentDeadline)>instant(reservedAt)&&instant(serverTime)>=instant(reservedAt));if("CANCELLED".equals(orderStatus))check(instant(closedAt)>=instant(reservedAt)&&instant(closedAt)<=instant(serverTime));else check(closedAt==null);
  var prior=order.evidence();if(prior!=null){
   check(prior.recordKind.equals(recordKind)&&Objects.equals(prior.orderId,orderId)&&Objects.equals(prior.teamId,teamId)&&Objects.equals(prior.reservedAt,reservedAt)&&Objects.equals(prior.paymentDeadline,paymentDeadline));
   if(version(prior.recordVersion)==version(recordVersion))check(Objects.equals(prior.orderStatus,orderStatus)&&Objects.equals(prior.closedAt,closedAt)&&prior.paymentPresent==paymentPresent&&prior.refundPresent==refundPresent);
   if(version(prior.teamVersion)==version(teamVersion))check(Objects.equals(prior.teamStatus,teamStatus));
  }
 }
 public boolean staleAgainst(ReservationEvidence prior){return prior!=null&&(version(recordVersion)<version(prior.recordVersion)||teamVersion!=null&&prior.teamVersion!=null&&version(teamVersion)<version(prior.teamVersion));}
 public static long version(String v){try{check(v!=null&&v.matches("[1-9][0-9]{0,18}"));return Long.parseLong(v);}catch(NumberFormatException e){throw new IllegalArgumentException("Unverifiable A version");}}
 public static long instant(String v){check(v!=null&&v.matches("[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z"));return Instant.parse(v).toEpochMilli();}
 private static void id(String v){check(v!=null&&v.matches("[A-Za-z0-9][A-Za-z0-9_-]{0,63}"));}
 private static void check(boolean ok){if(!ok)throw new IllegalArgumentException("Unverifiable A reservation");}
}
