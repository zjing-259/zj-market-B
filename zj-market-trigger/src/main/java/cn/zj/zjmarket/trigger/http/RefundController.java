package cn.zj.zjmarket.trigger.http;
import cn.zj.zjmarket.api.response.ApiResponse;
import cn.zj.zjmarket.domain.identity.model.valobj.AuthenticatedPrincipal;
import cn.zj.zjmarket.domain.refund.adapter.repository.*;
import cn.zj.zjmarket.domain.order.model.valobj.*;
import cn.zj.zjmarket.types.exception.AuthFailure;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.boot.autoconfigure.condition.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.*;
@RestController @RequestMapping("/api/v1") @ConditionalOnWebApplication(type=ConditionalOnWebApplication.Type.SERVLET) @ConditionalOnProperty(name="b.order.enabled",havingValue="true")
public final class RefundController {
 private final IRefundOperations ops;private final IRefundView views;
 public RefundController(IRefundOperations ops,IRefundView views){this.ops=ops;this.views=views;}
 @GetMapping("/orders/{orderId}/refund") public ApiResponse owner(@PathVariable String orderId,HttpServletRequest r){String actor=actor(r,false);query(r,Set.of());var data=new LinkedHashMap<String,Object>();data.put("orderId",orderId);data.put("refund",views.summary(actor,orderId));return ok(data,r);}
 @GetMapping("/admin/refund-exceptions") public ApiResponse list(HttpServletRequest r){String a=actor(r,true);return ok(ops.refunds(a,query(r,Set.of("page","size","fundsStatus","syncStatus","releaseStatus","alerted","orderId"))),r);}
 @GetMapping("/admin/refunds/{refundId}") public ApiResponse detail(@PathVariable String refundId,HttpServletRequest r){String a=actor(r,true);query(r,Set.of());return ok(ops.refund(a,refundId),r);}
 @GetMapping("/admin/reconciliations") public ApiResponse reconciliations(HttpServletRequest r){String a=actor(r,true);return ok(ops.reconciliations(a,query(r,Set.of("page","size","state","teamId","alerted"))),r);}
 @GetMapping("/admin/reconciliations/{taskId}") public ApiResponse reconciliation(@PathVariable String taskId,HttpServletRequest r){String a=actor(r,true);query(r,Set.of());return ok(ops.reconciliation(a,taskId),r);}
 @PostMapping("/admin/refunds/{refundId}/controls") public ResponseEntity<ApiResponse> control(@PathVariable String refundId,@RequestBody Map<String,Object> b,HttpServletRequest r){String a=actor(r,true);query(r,Set.of());if(!b.keySet().equals(Set.of("operationId","action","expectedVersion","reason")))throw PurchaseConditions.invalid();var c=new IRefundOperations.Control(text(b,"operationId"),text(b,"action"),ReservationEvidence.version(text(b,"expectedVersion")),text(b,"reason"));var result=ops.control(a,refundId,c);return ResponseEntity.status(result.replay()?200:202).body(ok(result.result(),r));}
 private static String text(Map<String,Object>b,String k){if(!(b.get(k) instanceof String s))throw PurchaseConditions.invalid();return s;}
 private static String actor(HttpServletRequest r,boolean operator){var p=(AuthenticatedPrincipal)r.getAttribute("b.principal");if(p==null)throw new AuthFailure(401,"AUTH_REQUIRED");if(operator&&!p.user().roles().contains("OPERATOR"))throw new AuthFailure(403,"FORBIDDEN");return p.user().userId();}
 private static Map<String,String> query(HttpServletRequest r,Set<String> keys){var filters=new HashMap<String,String>();r.getParameterMap().forEach((k,v)->{if(!keys.contains(k)||v.length!=1)throw PurchaseConditions.invalid();filters.put(k,v[0]);});return filters;}
 private static ApiResponse ok(Object data,HttpServletRequest r){return ApiResponse.ok(data,(String)r.getAttribute("b.requestId"));}
}
