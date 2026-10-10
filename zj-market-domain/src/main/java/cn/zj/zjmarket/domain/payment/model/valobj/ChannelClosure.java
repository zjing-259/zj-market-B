package cn.zj.zjmarket.domain.payment.model.valobj;
import java.util.List;
public record ChannelClosure(PaymentClose request,String gate,Long closedAt,List<ClosedAttempt> attempts,ChannelFact paid) {
 public ChannelClosure { attempts=List.copyOf(attempts); }
 public void validateUnpaid(PaymentClose expected,long now){
  if(!java.util.Objects.equals(request,expected)||!"CLOSED_UNPAID".equals(gate)||paid!=null||closedAt==null||closedAt<request.reservedAt()||closedAt>now||attempts.size()!=expected.attempts().size())throw new IllegalArgumentException("Invalid root close proof");
  for(int i=0;i<attempts.size();i++){var a=attempts.get(i);var e=expected.attempts().get(i);if(!a.attemptId().equals(e.attemptId())||a.attemptNo()!=e.attemptNo()||!a.requestHash().equals(e.requestHash())||a.transactionId()==null||!java.util.Set.of("FAILED","CLOSED_UNPAID").contains(a.state()))throw new IllegalArgumentException("Incomplete root close coverage");}
 }
}
