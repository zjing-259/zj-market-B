package cn.zj.zjmarket.domain.order.model.valobj;
import cn.zj.zjmarket.domain.product.model.valobj.TrialOffer;
import cn.zj.zjmarket.types.exception.OrderFailure;
import java.math.BigDecimal;
public record PurchaseConditions(String goodsId,String mode,String teamId,TrialOffer expectedOffer) {
 public PurchaseConditions {
  id(goodsId);
  if(!"OPEN".equals(mode) && !"JOIN".equals(mode))throw invalid();
  if("JOIN".equals(mode))id(teamId);else if(teamId!=null)throw invalid();
  var o=expectedOffer;if(o==null || !goodsId.equals(o.goodsId()) || !"CNY".equals(o.currency()) || o.targetCount()==null || o.targetCount()<1 || o.targetCount()>100)throw invalid();
  version(o.productVersion());version(o.activityId());
  var original=money(o.originalPrice(),false);var deduction=money(o.deductionPrice(),true);var pay=money(o.payPrice(),false);
  if(original.subtract(deduction).compareTo(pay)!=0)throw invalid();
 }
 public static void id(String id){if(id==null || !id.matches("[A-Za-z0-9][A-Za-z0-9_-]{0,63}"))throw invalid();}
 public static long version(String v){try{if(v==null || !v.matches("[1-9][0-9]{0,18}"))throw invalid();return Long.parseLong(v);}catch(NumberFormatException e){throw invalid();}}
 private static BigDecimal money(String v,boolean zero){if(v==null || !v.matches("(?:0|[1-9][0-9]{0,5})\\.[0-9]{2}"))throw invalid();var n=new BigDecimal(v);if(n.compareTo(zero?BigDecimal.ZERO:new BigDecimal("0.01"))<0)throw invalid();return n;}
 public static OrderFailure invalid(){return new OrderFailure(400,"VALIDATION_FAILED");}
}
