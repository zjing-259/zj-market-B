package cn.zj.zjmarket.domain.payment.model.valobj;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
import cn.zj.zjmarket.domain.order.model.valobj.ReservationEvidence;
import cn.zj.zjmarket.types.exception.OrderFailure;
import java.util.*;
/** Short-lived A evidence; monotonic clocks are never restored from durable tasks. */
public record Evidence(ReservationEvidence reservation,long started,long finished,long elapsedNanos,long maxRtt,long ttl,long skew,long receivedNanos){
  public Evidence(ReservationEvidence reservation,long started,long finished,long elapsedNanos,long maxRtt,long ttl,long skew){this(reservation,started,finished,elapsedNanos,maxRtt,ttl,skew,System.nanoTime());}
  public Evidence {if(maxRtt<1||ttl<1||skew<1||maxRtt>60000||ttl>60000||skew>60000)throw new IllegalArgumentException("Invalid payment time settings");}
  public void validate(MarketOrder order,long now){
   try{
    reservation.validate(order);
    if(reservation.staleAgainst(order.evidence())||!"RESERVATION".equals(reservation.recordKind())||!"RESERVED".equals(reservation.orderStatus())||!"FORMING".equals(reservation.teamStatus())||reservation.paymentPresent()||reservation.refundPresent())throw new IllegalArgumentException();
    long server=ReservationEvidence.instant(reservation.serverTime()),start=ReservationEvidence.instant(reservation.reservedAt()),end=ReservationEvidence.instant(reservation.paymentDeadline());
    long elapsed=elapsedNanos/1_000_000,age=System.nanoTime()-receivedNanos;
    if(age<0||age>ttl*1_000_000||elapsedNanos>maxRtt*1_000_000||finished<started||elapsedNanos<0||elapsed>maxRtt||finished-started>maxRtt||Math.abs((finished-started)-elapsed)>skew||server<started-skew||server>finished+skew||now<finished||now-finished>ttl||now-skew<start||now+skew>=end)throw new IllegalArgumentException();
   }catch(RuntimeException bad){throw new OrderFailure(503,"PAYMENT_TIME_UNVERIFIABLE");}
  }
 }
