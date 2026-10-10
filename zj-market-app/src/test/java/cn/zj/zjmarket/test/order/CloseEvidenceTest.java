package cn.zj.zjmarket.test.order;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
import cn.zj.zjmarket.domain.order.model.valobj.*;
class CloseEvidenceTest {
 static CloseEvidence close(String id,String team,String version){return new CloseEvidence("order",id,team,"CANCELLED","2026-10-09T10:00:00.000Z",version,id==null?null:"2");}
 @Test void markerCannotEraseKnownReservation(){var o=ReservationEvidenceTest.order();assertDoesNotThrow(()->close(null,null,"1").validate(o));var known=new MarketOrder(o.orderId(),o.purchaseIntentId(),o.requestHash(),o.confirmation(),o.businessStatus(),o.orderVersion(),o.createdAt(),o.reserveWaitDeadline(),true,o.paymentExposure(),ReservationEvidenceTest.result("2","team","RESERVED"),1,false,null);assertThrows(IllegalArgumentException.class,()->close(null,null,"3").validate(known));assertThrows(IllegalArgumentException.class,()->close("other","team","3").validate(known));assertThrows(IllegalArgumentException.class,()->close("a-order","team","1").validate(known));}
 @Test void closeRequiresExactVersionsAndAssociation(){assertDoesNotThrow(()->close("a-order","team","4294967297").validate(ReservationEvidenceTest.order()));for(String version:new String[]{"01","1.0","4294967297.1","9223372036854775808"})assertThrows(IllegalArgumentException.class,()->close("a-order","team",version).validate(ReservationEvidenceTest.order()));assertThrows(IllegalArgumentException.class,()->new CloseEvidence("other",null,null,"CANCELLED","2026-10-09T10:00:00.000Z","1",null).validate(ReservationEvidenceTest.order()));}
 @Test void summaryAloneCannotStandForFullQuery(){var proof=ReservationEvidenceTest.result("3","team","CANCELLED");assertThrows(IllegalArgumentException.class,()->close("a-order","team","3").validateQuery(proof));assertThrows(IllegalArgumentException.class,()->close("a-order","team","4").validateQuery(proof));}
}
