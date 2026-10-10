package cn.zj.zjmarket.domain.payment.model.valobj;
import java.util.List;
/** Frozen full attempt set, including attempts whose create has not reached the channel. */
public record PaymentClose(String paymentId,String closeId,String reason,String orderId,String userId,String source,String channel,String snapshotHash,String amount,String currency,long reservedAt,long deadline,List<CloseAttempt> attempts) {
 public PaymentClose { attempts=List.copyOf(attempts); }
}
