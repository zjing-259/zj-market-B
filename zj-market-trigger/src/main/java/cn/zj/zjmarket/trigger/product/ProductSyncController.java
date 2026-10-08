package cn.zj.zjmarket.trigger.product;
import cn.zj.zjmarket.application.product.*;
import cn.zj.zjmarket.application.identity.*;
import cn.zj.zjmarket.domain.product.Product;
import cn.zj.zjmarket.trigger.identity.ApiResponse;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import org.springframework.boot.autoconfigure.condition.*;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;
@RestController @RequestMapping("/api/v1/admin")
@ConditionalOnWebApplication(type=ConditionalOnWebApplication.Type.SERVLET)
@ConditionalOnProperty(name="b.sync.enabled",havingValue="true")
public final class ProductSyncController {
 private final ProductSyncService service;
 public ProductSyncController(ProductSyncService service){this.service=service;}
 @GetMapping("/products/{id}/sync") ApiResponse status(@PathVariable String id,HttpServletRequest req){operator(req);query(req,Set.of());return ok(service.progress(id),req);}
 @PostMapping("/products/{id}/sync/retries") ResponseEntity<ApiResponse> retry(@PathVariable String id,@RequestBody Map<String,Object> body,HttpServletRequest req){var p=operator(req);query(req,Set.of());String event=event(body);long version=version(body);service.retry(id,event,version,p.user().userId());return ResponseEntity.accepted().body(ok(Map.of("eventId",event,"status","QUEUED"),req));}
 @PostMapping("/products/{id}/sync/pauses") ApiResponse pause(@PathVariable String id,@RequestBody Map<String,Object> body,HttpServletRequest req){var p=operator(req);query(req,Set.of());service.pause(id,event(body),version(body),p.user().userId());return ok(service.progress(id),req);}
 @GetMapping("/sync/quarantine") ApiResponse quarantine(HttpServletRequest req){operator(req);query(req,Set.of("page","size"));var page=service.quarantined(number(req,"page",1),number(req,"size",20));return ok(Map.of("items",page.items().stream().map(q -> Map.of("quarantineId",q.quarantineId(),"bodyHash",q.bodyHash(),"reason",q.reason(),"originalSize",q.originalSize(),"storedAt",DateTimeFormatter.ofPattern("uuuu-MM-dd'T'HH:mm:ss.SSS'Z'").withZone(ZoneOffset.UTC).format(Instant.ofEpochMilli(q.storedAt())),"state",q.state())).toList(),"page",page.page(),"size",page.size(),"total",page.total()),req);}
 private static String event(Map<String,Object> body){if(!body.keySet().equals(Set.of("eventId","expectedVersion")) || !(body.get("eventId") instanceof String id) || !id.matches("[A-Za-z0-9._-]{1,64}"))throw invalid();return id;}
 private static long version(Map<String,Object> body){try{if(!(body.get("expectedVersion") instanceof String v))throw invalid();return Product.parseVersion(v);}catch(IllegalArgumentException e){throw invalid();}}
 private static int number(HttpServletRequest req,String key,int fallback){var v=req.getParameter(key);if(v==null)return fallback;try{if(!v.matches("[1-9][0-9]{0,9}"))throw invalid();return Integer.parseInt(v);}catch(NumberFormatException e){throw invalid();}}
 private static void query(HttpServletRequest req,Set<String> names){if(req.getParameterMap().entrySet().stream().anyMatch(e -> !names.contains(e.getKey()) || e.getValue().length!=1))throw invalid();}
 private static IdentityService.Principal operator(HttpServletRequest req){var p=(IdentityService.Principal)req.getAttribute("b.principal");if(p==null)throw new AuthFailure(401,"AUTH_REQUIRED");if(!p.user().roles().contains("OPERATOR"))throw new AuthFailure(403,"FORBIDDEN");return p;}
 private static ProductFailure invalid(){return new ProductFailure(400,"VALIDATION_FAILED");}
 private static ApiResponse ok(Object data,HttpServletRequest req){return ApiResponse.ok(data,(String)req.getAttribute("b.requestId"));}
}
