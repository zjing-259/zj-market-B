package cn.zj.zjmarket.domain.refund.model;

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.Set;

/** Business refund identity is stable; only a confirmed failed attempt permits another attempt. */
public final class Refund {
 private Refund(){}
 public static void require(boolean value){if(!value)throw new IllegalArgumentException("Refund evidence conflict");}
 public static String hash(String value){try{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));}catch(Exception e){throw new IllegalStateException(e);}}
 public record Settings(long scanMillis,long timeoutMillis,long leaseMillis,long renewMillis,long retryBaseMillis,long retryCapMillis,long jitterMillis){
  public Settings{require(scanMillis>0&&timeoutMillis>0&&leaseMillis>timeoutMillis&&renewMillis>0&&renewMillis<leaseMillis&&retryBaseMillis>0&&retryCapMillis>=retryBaseMillis&&jitterMillis>=0&&jitterMillis<=1000);}
  public static Settings defaults(){return new Settings(2000,10000,30000,20000,2000,30000,250);}
  public long delay(int failures){long factor=1L<<Math.min(20,Math.max(0,failures-1));long base=retryBaseMillis>retryCapMillis/factor?retryCapMillis:retryBaseMillis*factor;return Math.min(retryCapMillis,base)+(jitterMillis==0?0:java.util.concurrent.ThreadLocalRandom.current().nextLong(jitterMillis+1));}
 }
 public record Request(String refundId,String orderId,String paymentId,String paymentAttemptId,String paymentTransactionId,long paidAt,String paymentSnapshotHash,String paymentSuccessHash,String amount,String currency,String attemptId,int attemptNo){
  public Request{for(String id:new String[]{refundId,orderId,paymentId,paymentAttemptId,paymentTransactionId,attemptId})require(id!=null&&id.matches("[A-Za-z0-9][A-Za-z0-9_-]{0,63}"));require(paymentSnapshotHash!=null&&paymentSnapshotHash.matches("[0-9a-f]{64}")&&paymentSuccessHash!=null&&paymentSuccessHash.matches("[0-9a-f]{64}"));require(amount!=null&&amount.matches("[0-9]{1,8}\\.[0-9]{2}")&&new BigDecimal(amount).signum()>0&&"CNY".equals(currency)&&paidAt>0&&attemptNo>0);}
  public String canonical(){return String.join("|",refundId,orderId,paymentId,paymentAttemptId,paymentTransactionId,Long.toString(paidAt),paymentSnapshotHash,paymentSuccessHash,amount,currency,attemptId,Integer.toString(attemptNo));}
  public String hash(){return Refund.hash(canonical());}
  public boolean sameRoot(Request other){return other!=null&&refundId.equals(other.refundId)&&orderId.equals(other.orderId)&&paymentId.equals(other.paymentId)&&paymentAttemptId.equals(other.paymentAttemptId)&&paymentTransactionId.equals(other.paymentTransactionId)&&paidAt==other.paidAt&&paymentSnapshotHash.equals(other.paymentSnapshotHash)&&paymentSuccessHash.equals(other.paymentSuccessHash)&&amount.equals(other.amount)&&currency.equals(other.currency);}
 }
 public record Fact(Request request,String status,String transactionId,Long refundedAt,long version){
  public void validate(Request expected,long now){require(request!=null&&request.equals(expected)&&status!=null&&Set.of("UNKNOWN","FAILED","SUCCEEDED").contains(status)&&version==1);if("UNKNOWN".equals(status)){require(transactionId==null&&refundedAt==null);return;}require(transactionId!=null&&transactionId.matches("[A-Za-z0-9][A-Za-z0-9_-]{0,63}"));if(status.equals("SUCCEEDED"))require(refundedAt!=null&&refundedAt>=request.paidAt&&refundedAt<=now);else require(refundedAt==null);}
 }
 public record Lease(Request request,String token,long intentVersion,boolean checkOnly){public Lease(Request request,String token,long intentVersion){this(request,token,intentVersion,false);}}
 public record Notice(String id,String refundId,String attemptId,String token,int failures){}
}
