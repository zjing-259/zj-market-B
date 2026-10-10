package cn.zj.zjmarket.test.order;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import cn.zj.zjmarket.domain.order.adapter.port.ITradePort;
import cn.zj.zjmarket.domain.order.adapter.repository.IOrderRepository;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
import cn.zj.zjmarket.domain.order.model.valobj.TeamView;
import cn.zj.zjmarket.domain.order.service.impl.TeamService;
import cn.zj.zjmarket.types.exception.OrderFailure;
class TeamServiceTest {
 static TeamView view(){return new TeamView("team","sku","1","FORMING","1",2,1,0,"2026-10-09T10:00:00.000Z","2026-10-09T10:15:00.000Z","2026-10-09T10:00:01.000Z",true,"order");}
 @Test void upstreamOwnRecordWithoutLocalOwnerIsHidden(){var port=mock(ITradePort.class);var orders=mock(IOrderRepository.class);when(port.team("user","team","request")).thenReturn(view());assertNull(new TeamService(port,orders).query("user","team","request").myOrderId());}
 @Test void knownOwnRecordMustBelongToRequestedTeam(){var port=mock(ITradePort.class);var orders=mock(IOrderRepository.class);when(port.team("user","team","request")).thenReturn(view());var o=ReservationEvidenceTest.order();var bad=new MarketOrder(o.orderId(),o.purchaseIntentId(),o.requestHash(),o.confirmation(),o.businessStatus(),o.orderVersion(),o.createdAt(),o.reserveWaitDeadline(),true,o.paymentExposure(),ReservationEvidenceTest.result("1","different-team","RESERVED"),1,false,null);when(orders.byId("user","order")).thenReturn(bad);assertEquals("UPSTREAM_RESPONSE_INVALID",assertThrows(OrderFailure.class,()->new TeamService(port,orders).query("user","team","request")).code());}
 @Test void validatedOwnOrderCanBeLinked(){var port=mock(ITradePort.class);var orders=mock(IOrderRepository.class);when(port.team("user","team","request")).thenReturn(view());var o=ReservationEvidenceTest.order();var known=new MarketOrder(o.orderId(),o.purchaseIntentId(),o.requestHash(),o.confirmation(),o.businessStatus(),o.orderVersion(),o.createdAt(),o.reserveWaitDeadline(),true,o.paymentExposure(),ReservationEvidenceTest.result("1","team","RESERVED"),1,false,null);when(orders.byId("user","order")).thenReturn(known);assertEquals("order",new TeamService(port,orders).query("user","team","request").myOrderId());}
}
