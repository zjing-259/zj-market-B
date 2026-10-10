package cn.zj.zjmarket.test.order;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import cn.zj.zjmarket.domain.order.model.entity.*;
import cn.zj.zjmarket.domain.order.model.valobj.*;
class ReservationEvidenceTest {
 static MarketOrder order(){return new MarketOrder("order","intent","hash",new PurchaseConfirmation("confirm","user","s","c",OrderServiceTest.conditions(),"name",null,1,300001,1L),"PROCESSING",1,1,300001,true,"NEVER_OPENED");}
 static ReservationEvidence result(String version,String team,String status){return new ReservationEvidence("RESERVATION","a-order","order","user","s","c","1","sku","1",1,team,"10.00","1.00","9.00","CNY","2026-10-09T10:00:00.000Z","2026-10-09T10:15:00.000Z",status,"FORMING",version,"1","2026-10-09T10:00:01.000Z",null,false,false);}
 @Test void exactVersionsAndRequiredTimes(){assertDoesNotThrow(()->result("4294967297","team","RESERVED").validate(order()));for(String v:new String[]{"0","01","1.0","9223372036854775808","-1"})assertThrows(IllegalArgumentException.class,()->result(v,"team","RESERVED").validate(order()));assertThrows(IllegalArgumentException.class,()->ReservationEvidence.instant("2026-10-09T10:00:00Z"));}
 @Test void sameVersionCannotChangeFacts(){var o=order();var saved=new MarketOrder(o.orderId(),o.purchaseIntentId(),o.requestHash(),o.confirmation(),o.businessStatus(),o.orderVersion(),o.createdAt(),o.reserveWaitDeadline(),true,o.paymentExposure(),result("2","team","RESERVED"),1,false,null);assertThrows(IllegalArgumentException.class,()->result("2","team","PAID").validate(saved));assertThrows(IllegalArgumentException.class,()->result("3","different-team","RESERVED").validate(saved));assertTrue(result("1","team","RESERVED").staleAgainst(saved.evidence()));}
 @Test void closeMarkerIsNotAnAbsentOrder(){var marker=new ReservationEvidence("CLOSE_MARKER",null,"order","user","s","c",null,null,null,null,null,null,null,null,null,null,null,"CANCELLED",null,"1",null,"2026-10-09T10:00:01.000Z","2026-10-09T10:00:00.000Z",false,false);assertDoesNotThrow(()->marker.validate(order()));}
}
