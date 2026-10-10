package cn.zj.zjmarket.trigger.http;
import cn.zj.zjmarket.api.response.ApiResponse;
import cn.zj.zjmarket.domain.identity.model.valobj.AuthenticatedPrincipal;
import cn.zj.zjmarket.domain.payment.model.valobj.Accepted;
import cn.zj.zjmarket.domain.payment.service.IPaymentService;
import cn.zj.zjmarket.domain.payment.service.impl.PaymentService;
import cn.zj.zjmarket.types.exception.*;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.*;
@RestController @RequestMapping("/api/v1")
@ConditionalOnWebApplication(type=ConditionalOnWebApplication.Type.SERVLET)
@ConditionalOnProperty(name="b.payment.enabled",havingValue="true")
public final class PaymentController {
 private final IPaymentService service;private final String origin;
 public PaymentController(IPaymentService service,@Value("${b.identity.origin:}")String origin){this.service=service;this.origin=origin;}
 @GetMapping("/orders/{orderId}/payment") ApiResponse forOrder(@PathVariable String orderId,HttpServletRequest r){return ok(service.forOrder(actor(r,false),orderId),r);}
 @GetMapping("/payments/{paymentId}") ApiResponse payment(@PathVariable String paymentId,HttpServletRequest r){return ok(service.payment(actor(r,false),paymentId),r);}
 @GetMapping("/payments/{paymentId}/attempts/{attemptId}") ApiResponse attempt(@PathVariable String paymentId,@PathVariable String attemptId,HttpServletRequest r){return ok(service.attempt(actor(r,false),paymentId,attemptId),r);}
 @GetMapping("/orders/{orderId}/payment-operations/{operationId}") ApiResponse operation(@PathVariable String orderId,@PathVariable String operationId,HttpServletRequest r){return ok(service.operation(actor(r,false),orderId,operationId),r);}
 @PostMapping("/orders/{orderId}/payment-attempts") ResponseEntity<ApiResponse> create(@PathVariable String orderId,@RequestBody Map<String,Object> b,HttpServletRequest r){String actor=actor(r,true);if(!b.keySet().equals(Set.of("operationId","previousAttemptId"))||b.get("previousAttemptId")!=null&&!(b.get("previousAttemptId") instanceof String))throw invalid();return accepted(service.create(actor,orderId,text(b,"operationId"),(String)b.get("previousAttemptId"),id(r)),r);}
 @PostMapping("/payments/{paymentId}/attempts/{attemptId}/simulated-results") ResponseEntity<ApiResponse> choose(@PathVariable String paymentId,@PathVariable String attemptId,@RequestBody Map<String,Object> b,HttpServletRequest r){String actor=actor(r,true);if(!b.keySet().equals(Set.of("operationId","result")))throw invalid();return accepted(service.choose(actor,paymentId,attemptId,text(b,"operationId"),text(b,"result"),id(r)),r);}
 private String actor(HttpServletRequest r,boolean write){var p=(AuthenticatedPrincipal)r.getAttribute("b.principal");if(p==null)throw new AuthFailure(401,"AUTH_REQUIRED");if(!p.user().roles().contains("USER")&&!p.user().roles().contains("OPERATOR"))throw new AuthFailure(403,"FORBIDDEN");if(!r.getParameterMap().isEmpty())throw invalid();if(write&&!origin.equals(r.getHeader("Origin")))throw new AuthFailure(403,"FORBIDDEN");return p.user().userId();}
 private ResponseEntity<ApiResponse> accepted(Accepted a,HttpServletRequest r){return ResponseEntity.status(!a.receipt().accepted()?409:a.replay()||a.applied()?200:202).body(new ApiResponse(a.receipt().accepted()?"0000":a.receipt().errorCode(),a.receipt().accepted()?"success":a.receipt().errorCode(),PaymentService.receipt(a.receipt()),id(r)));}
 private static String text(Map<String,Object> b,String key){if(!(b.get(key) instanceof String v))throw invalid();return v;}
 private static OrderFailure invalid(){return new OrderFailure(400,"VALIDATION_FAILED");}
 private static String id(HttpServletRequest r){return (String)r.getAttribute("b.requestId");}
 private static ApiResponse ok(Object data,HttpServletRequest r){return ApiResponse.ok(data,id(r));}
}
