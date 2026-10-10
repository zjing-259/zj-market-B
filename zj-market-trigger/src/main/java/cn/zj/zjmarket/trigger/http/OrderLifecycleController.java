package cn.zj.zjmarket.trigger.http;
import cn.zj.zjmarket.api.response.ApiResponse;
import cn.zj.zjmarket.domain.identity.model.valobj.AuthenticatedPrincipal;
import cn.zj.zjmarket.domain.order.service.IOrderLifecycleService;
import cn.zj.zjmarket.domain.order.model.entity.MarketOrder;
import cn.zj.zjmarket.domain.order.model.valobj.*;
import cn.zj.zjmarket.types.exception.AuthFailure;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.boot.autoconfigure.condition.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.*;
@RestController @RequestMapping("/api/v1") @ConditionalOnWebApplication(type=ConditionalOnWebApplication.Type.SERVLET) @ConditionalOnProperty(name="b.trade.enabled",havingValue="true")
public final class OrderLifecycleController {
 private final IOrderLifecycleService service;public OrderLifecycleController(IOrderLifecycleService s){service=s;}
 @PostMapping("/orders/{orderId}/cancel") ResponseEntity<ApiResponse> cancel(@PathVariable String orderId,@RequestBody Map<String,Object> b,HttpServletRequest r){String a=actor(r,false);query(r,Set.of());if(!b.keySet().equals(Set.of("operationId","reason")))throw PurchaseConditions.invalid();var result=service.cancel(a,orderId,text(b,"operationId"),text(b,"reason"));var order=(MarketOrder)result.result();return ResponseEntity.status(result.replay()||"CLOSED".equals(order.businessStatus())?200:202).body(ok(OrderController.order(order),r));}
 @GetMapping("/admin/orders/exceptions") ApiResponse exceptions(HttpServletRequest r){String a=actor(r,true);query(r,Set.of("page","size","status","paused","reviewRequired"));return ok(service.exceptions(a,integer(r,"page",1),integer(r,"size",20),r.getParameter("status"),bool(r,"paused"),bool(r,"reviewRequired")),r);}
 @GetMapping("/admin/orders/{orderId}/coordination") ApiResponse coordination(@PathVariable String orderId,HttpServletRequest r){String a=actor(r,true);query(r,Set.of());return ok(service.coordination(a,orderId),r);}
 @PostMapping("/admin/orders/{orderId}/coordination-controls") ResponseEntity<ApiResponse> control(@PathVariable String orderId,@RequestBody Map<String,Object> b,HttpServletRequest r){String a=actor(r,true);query(r,Set.of());if(!b.keySet().equals(Set.of("operationId","action","expectedVersion","reason")))throw PurchaseConditions.invalid();long version=ReservationEvidence.version(text(b,"expectedVersion"));var result=service.control(a,orderId,new OrderControl(text(b,"operationId"),version,text(b,"action"),text(b,"reason")));return ResponseEntity.status(result.replay()?200:202).body(ok(result.result(),r));}
 private static String actor(HttpServletRequest r,boolean op){var p=(AuthenticatedPrincipal)r.getAttribute("b.principal");if(p==null)throw new AuthFailure(401,"AUTH_REQUIRED");if(op&&!p.user().roles().contains("OPERATOR"))throw new AuthFailure(403,"FORBIDDEN");return p.user().userId();}
 private static String text(Map<String,Object>b,String k){if(!(b.get(k) instanceof String v))throw PurchaseConditions.invalid();return v;}
 private static Boolean bool(HttpServletRequest r,String k){String s=r.getParameter(k);if(s==null)return null;if(!Set.of("true","false").contains(s))throw PurchaseConditions.invalid();return Boolean.valueOf(s);}
 private static int integer(HttpServletRequest r,String k,int fallback){String s=r.getParameter(k);if(s==null)return fallback;try{if(!s.matches("[1-9][0-9]{0,9}"))throw PurchaseConditions.invalid();return Integer.parseInt(s);}catch(NumberFormatException e){throw PurchaseConditions.invalid();}}
 private static void query(HttpServletRequest r,Set<String> allowed){if(r.getParameterMap().entrySet().stream().anyMatch(e->!allowed.contains(e.getKey())||e.getValue().length!=1))throw PurchaseConditions.invalid();}
 private static ApiResponse ok(Object v,HttpServletRequest r){return ApiResponse.ok(v,(String)r.getAttribute("b.requestId"));}
}
