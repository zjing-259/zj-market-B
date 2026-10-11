package cn.zj.zjmarket.domain.reconciliation.model;

import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
import cn.zj.zjmarket.domain.order.model.valobj.ReservationEvidence;
import cn.zj.zjmarket.domain.order.model.valobj.PurchaseConditions;
import java.util.*;
import java.math.BigDecimal;

/** Immutable business evidence; transport DTOs stay outside the domain. */
public final class Reconciliation {
 private Reconciliation(){}
 public record Paid(String paymentId,String paidAmount,String currency,String paidAt){
  public void validate(){id(paymentId);money(paidAmount);require("CNY".equals(currency));ReservationEvidence.instant(paidAt);}
 }
 public record Team(String teamId,String status,String version,String goodsId,String activityId,String validEndTime,String serverTime){
  public void validate(String expected){require(expected.equals(teamId));id(teamId);id(goodsId);ReservationEvidence.version(activityId);ReservationEvidence.version(version);ReservationEvidence.instant(validEndTime);ReservationEvidence.instant(serverTime);require(Set.of("FORMING","RECONCILING","COMPLETED","FAILED").contains(status));}
 }
 public record Member(String userId,String outTradeNo,String orderId,String orderStatus,String reservedAt,String paymentDeadline,String payPrice,String currency,Paid payment){
  public void validate(){id(userId);id(outTradeNo);id(orderId);require(Set.of("RESERVED","PAID","CANCELLED").contains(orderStatus));require(ReservationEvidence.instant(reservedAt)<ReservationEvidence.instant(paymentDeadline));money(payPrice);require("CNY".equals(currency));require((payment!=null)=="PAID".equals(orderStatus));if(payment!=null)payment.validate();}
  public boolean sameFrozen(Member m){return userId.equals(m.userId)&&outTradeNo.equals(m.outTradeNo)&&orderId.equals(m.orderId)&&reservedAt.equals(m.reservedAt)&&paymentDeadline.equals(m.paymentDeadline)&&payPrice.equals(m.payPrice)&&currency.equals(m.currency);}
 }
 public record Roster(String reconciliationId,String rosterVersion,String teamStatus,String teamVersion,String validEndTime,List<Member> members){
  public Roster {members=members==null?null:List.copyOf(members);}
  public void validate(){id(reconciliationId);id(rosterVersion);ReservationEvidence.version(teamVersion);ReservationEvidence.instant(validEndTime);require(Set.of("RECONCILING","FAILED","COMPLETED").contains(teamStatus));require(members!=null&&members.size()<=100);var seen=new HashSet<String>();for(var m:members){m.validate();require(seen.add(m.outTradeNo));}}
 }
 public record Trade(ReservationEvidence evidence,Paid payment){public void validate(MarketOrder order){require(evidence!=null);evidence.validate(order);require(!evidence.staleAgainst(order.evidence()));require(evidence.paymentPresent()==(payment!=null));if(payment!=null)payment.validate();}}
 public record Decision(String userId,String outTradeNo,String disposition,String paymentId,String closeId,String paidAt,String paidAmount,String currency,String refundId){
  public void validate(){id(userId);id(outTradeNo);switch(disposition){case "PAID_ACCEPTED" -> {id(paymentId);require(closeId==null&&paidAt==null&&paidAmount==null&&currency==null&&refundId==null);}case "CLOSED_UNPAID" -> {id(closeId);require(paymentId==null&&paidAt==null&&paidAmount==null&&currency==null&&refundId==null);}case "PAID_OUTSIDE_WINDOW" -> {id(paymentId);id(refundId);ReservationEvidence.instant(paidAt);money(paidAmount);require("CNY".equals(currency)&&closeId==null);}default -> throw new IllegalArgumentException("Unknown reconciliation disposition");}}
 }
 public record Completion(String source,String channel,String teamId,String reconciliationId,String rosterVersion,String completionId,String checkedAt,List<Decision> results){
  public Completion {results=results==null?null:List.copyOf(results);}
  public void validate(List<Member> roster){id(completionId);ReservationEvidence.instant(checkedAt);require(results!=null&&results.size()==roster.size());var expected=new HashMap<String,String>();for(var m:roster){m.validate();require(expected.put(m.outTradeNo,m.userId)==null);}var seen=new HashSet<String>();for(var d:results){d.validate();require(seen.add(d.outTradeNo)&&Objects.equals(expected.get(d.outTradeNo),d.userId));}}
 }
 public record Result(String teamId,String reconciliationId,String teamStatus,String teamVersion,String resolvedAt){public void validate(Completion c){require(c.teamId.equals(teamId)&&c.reconciliationId.equals(reconciliationId));require(Set.of("FAILED","COMPLETED").contains(teamStatus));ReservationEvidence.version(teamVersion);ReservationEvidence.instant(resolvedAt);}}
 public record Lease(String taskId,String teamId,String token,long intentVersion){}
 public record Local(MarketOrder order,String paymentId,List<String> attemptIds){}
 public static boolean inWindow(long paidAt,long start,long deadline){return paidAt>=start&&paidAt<deadline;}
 private static void id(String value){require(value!=null&&value.matches("[A-Za-z0-9][A-Za-z0-9_-]{0,63}"));}
 public static void require(boolean ok){if(!ok)throw new IllegalArgumentException("Unverifiable reconciliation evidence");}
 private static void money(String s){require(s!=null&&s.matches("(0|[1-9][0-9]*)\\.[0-9]{2}")&&new BigDecimal(s).signum()>0);}
}
