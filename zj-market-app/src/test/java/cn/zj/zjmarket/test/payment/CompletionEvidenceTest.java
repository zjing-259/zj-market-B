package cn.zj.zjmarket.test.payment;
import cn.zj.zjmarket.domain.order.model.entity.*;
import cn.zj.zjmarket.domain.order.model.valobj.*;
import cn.zj.zjmarket.domain.payment.model.valobj.*;
import cn.zj.zjmarket.domain.product.model.valobj.TrialOffer;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
class CompletionEvidenceTest {
 private static MarketOrder order(){var q=new PurchaseConditions("sku","OPEN",null,new TrialOffer("1","sku","1","10.00","1.00","9.00","CNY",2));var c=new PurchaseConfirmation("c","u","s","c",q,"sku",null,1,2,1L);var a=new ReservationEvidence("RESERVATION","a","o","u","s","c","1","sku","1",1,"t","10.00","1.00","9.00","CNY","2026-10-10T00:00:00.000Z","2026-10-10T00:15:00.000Z","PAID","FORMING","2","2","2026-10-10T00:00:01.000Z",null,true,false);return new MarketOrder("o","i","h",c,"PAID_WAITING_TEAM",2,1,2,true,"POSSIBLY_OPENED",a,2,false,null);}
 private static Payment payment(String funds,String accepted){return new Payment("p","o","u",2,funds,"PAID",accepted,"9.00","CNY",2,ReservationEvidence.instant("2026-10-10T00:00:01.000Z"),"at","at",false,null);}
 private static CompletionEvidence evidence(String id,String amount,String paidAt,String version){return new CompletionEvidence("a","o","t","PAID","COMPLETED","2",version,id,amount,"CNY",paidAt);}
 @Test void requiresExactPaymentIdentityAmountAndTime(){assertDoesNotThrow(()->evidence("p","9.00","2026-10-10T00:00:01.000Z","3").validate(order(),payment("SUCCEEDED","ACCEPTED")));assertThrows(IllegalArgumentException.class,()->evidence("other","9.00","2026-10-10T00:00:01.000Z","3").validate(order(),payment("SUCCEEDED","ACCEPTED")));assertThrows(IllegalArgumentException.class,()->evidence("p","9.01","2026-10-10T00:00:01.000Z","3").validate(order(),payment("SUCCEEDED","ACCEPTED")));assertThrows(IllegalArgumentException.class,()->evidence("p","9.00","2026-10-10T00:00:01.001Z","3").validate(order(),payment("SUCCEEDED","ACCEPTED")));}
 @Test void teamCompletionCannotReplaceMoneyOrAcceptance(){var e=evidence("p","9.00","2026-10-10T00:00:01.000Z","3");for(String state:new String[]{"UNPAID","UNKNOWN"})assertThrows(IllegalArgumentException.class,()->e.validate(order(),payment(state,"ACCEPTED")));for(String accepted:new String[]{"PENDING","REJECTED","REVIEW_REQUIRED"})assertThrows(IllegalArgumentException.class,()->e.validate(order(),payment("SUCCEEDED",accepted)));}
 @Test void versionsRemainExactAndCannotOverflow(){assertDoesNotThrow(()->evidence("p","9.00","2026-10-10T00:00:01.000Z","4294967297").validate(order(),payment("SUCCEEDED","ACCEPTED")));for(String v:new String[]{"01","0","-1","9223372036854775808"})assertThrows(IllegalArgumentException.class,()->evidence("p","9.00","2026-10-10T00:00:01.000Z",v).validate(order(),payment("SUCCEEDED","ACCEPTED")));}
}
