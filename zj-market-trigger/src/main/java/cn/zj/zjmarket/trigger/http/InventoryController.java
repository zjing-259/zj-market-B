package cn.zj.zjmarket.trigger.http;
import cn.zj.zjmarket.api.response.ApiResponse;
import cn.zj.zjmarket.domain.identity.model.valobj.AuthenticatedPrincipal;
import cn.zj.zjmarket.domain.inventory.service.IInventoryService;
import cn.zj.zjmarket.domain.inventory.model.entity.InventoryAccount;
import cn.zj.zjmarket.domain.inventory.model.valobj.*;
import cn.zj.zjmarket.types.exception.*;
import jakarta.servlet.http.HttpServletRequest;
import java.time.Instant;
import java.util.*;
import org.springframework.boot.autoconfigure.condition.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
@RestController @RequestMapping("/api/v1/admin/inventory")
@ConditionalOnWebApplication(type=ConditionalOnWebApplication.Type.SERVLET)
@ConditionalOnProperty(name="b.inventory.enabled",havingValue="true")
public final class InventoryController {
 private final IInventoryService service;public InventoryController(IInventoryService service){this.service=service;}
 @GetMapping ApiResponse list(HttpServletRequest req){actor(req);query(req,Set.of("page","size","goodsId"));var p=service.list(number(req,"page",1),number(req,"size",20),req.getParameter("goodsId"));return ok(Map.of("items",p.items().stream().map(InventoryController::account).toList(),"page",p.page(),"size",p.size(),"total",p.total()),req);}
 @GetMapping("/{goodsId}") ApiResponse detail(@PathVariable String goodsId,HttpServletRequest req){actor(req);query(req,Set.of());return ok(account(service.detail(goodsId)),req);}
 @GetMapping("/operations/{operationId}") ApiResponse operation(@PathVariable String operationId,HttpServletRequest req){var actor=actor(req);query(req,Set.of());return ok(result(service.operation(actor,operationId)),req);}
 @GetMapping("/{goodsId}/ledger") ApiResponse ledger(@PathVariable String goodsId,HttpServletRequest req){actor(req);query(req,Set.of("page","size"));var p=service.ledger(goodsId,number(req,"page",1),number(req,"size",20));return ok(Map.of("items",p.items().stream().map(InventoryController::ledgerDto).toList(),"page",p.page(),"size",p.size(),"total",p.total()),req);}
 @PostMapping("/{goodsId}/inbounds") ResponseEntity<ApiResponse> inbound(@PathVariable String goodsId,@RequestBody Map<String,Object> body,HttpServletRequest req){return execute(goodsId,body,req,true);}
 @PostMapping("/{goodsId}/adjustments") ResponseEntity<ApiResponse> adjust(@PathVariable String goodsId,@RequestBody Map<String,Object> body,HttpServletRequest req){return execute(goodsId,body,req,false);}
 private ResponseEntity<ApiResponse> execute(String id,Map<String,Object> body,HttpServletRequest req,boolean inbound){
  String actor=actor(req);query(req,Set.of());
  if(!body.keySet().equals(Set.of("operationId",inbound?"quantity":"delta","expectedVersion","reason")))throw invalid();
  long delta=parse(text(body,inbound?"quantity":"delta"),inbound),version=parse(text(body,"expectedVersion"),true);
  var write=service.execute(actor,text(body,"operationId"),new InventoryRequest(inbound?"INBOUND":"ADJUST",id,delta,version,text(body,"reason")));
  var r=write.result();if(r.outcome().equals("REJECTED"))return ResponseEntity.status(409).body(new ApiResponse(r.code(),r.message(),Map.of("inventoryOperation",result(r)),requestId(req)));
  return ResponseEntity.status(write.replay()?200:201).body(ok(result(r),req));
 }
 private static long parse(String v,boolean positive){if(!v.matches(positive?"[1-9][0-9]{0,18}":"-?[1-9][0-9]{0,18}"))throw invalid();try{return Long.parseLong(v);}catch(NumberFormatException e){throw invalid();}}
 private static String text(Map<String,Object> b,String k){if(!(b.get(k) instanceof String s))throw invalid();return s;}
 private static int number(HttpServletRequest r,String n,int fallback){var s=r.getParameter(n);if(s==null)return fallback;if(!s.matches("[1-9][0-9]{0,9}"))throw invalid();try{return Integer.parseInt(s);}catch(NumberFormatException e){throw invalid();}}
 private static void query(HttpServletRequest req,Set<String> names){if(req.getParameterMap().entrySet().stream().anyMatch(e -> !names.contains(e.getKey())||e.getValue().length!=1))throw invalid();}
 private static String actor(HttpServletRequest r){var p=(AuthenticatedPrincipal)r.getAttribute("b.principal");if(p==null)throw new AuthFailure(401,"AUTH_REQUIRED");if(!p.user().roles().contains("OPERATOR"))throw new AuthFailure(403,"FORBIDDEN");return p.user().userId();}
 private static InventoryFailure invalid(){return new InventoryFailure(400,"VALIDATION_FAILED");}
 private static String requestId(HttpServletRequest r){return (String)r.getAttribute("b.requestId");}
 private static ApiResponse ok(Object data,HttpServletRequest req){return ApiResponse.ok(data,requestId(req));}
 private static String time(long t){return new java.time.format.DateTimeFormatterBuilder().appendInstant(3).toFormatter().format(Instant.ofEpochMilli(t));}
 public static Map<String,Object> account(InventoryAccount a){return Map.of("goodsId",a.goodsId(),"available",Long.toString(a.available()),"reserved",Long.toString(a.reserved()),"sold",Long.toString(a.sold()),"version",Long.toString(a.version()),"updatedAt",time(a.updatedAt()));}
 private static Map<String,Object> result(InventoryResult r){var q=r.request();return Map.of("operationId",r.operationId(),"request",Map.of("kind",q.kind(),"goodsId",q.goodsId(),"delta",Long.toString(q.delta()),"expectedVersion",Long.toString(q.expectedVersion()),"reason",q.reason()),"outcome",r.outcome(),"code",r.code(),"message",r.message(),"completedAt",time(r.completedAt()),"inventory",account(r.inventory()));}
 private static Map<String,Object> ledgerDto(InventoryLedger r){var d=new LinkedHashMap<String,Object>();d.put("ledgerId",r.ledgerId());d.put("actorId",r.actorId());d.put("goodsId",r.goodsId());d.put("operationId",r.operationId());d.put("orderId",r.orderId());d.put("kind",r.kind());d.put("before",Map.of("available",Long.toString(r.beforeAvailable()),"reserved",Long.toString(r.beforeReserved()),"sold",Long.toString(r.beforeSold())));d.put("after",Map.of("available",Long.toString(r.afterAvailable()),"reserved",Long.toString(r.reserved()),"sold",Long.toString(r.sold())));d.put("delta",Map.of("available",Long.toString(r.delta()),"reserved",Long.toString(r.reserved()-r.beforeReserved()),"sold",Long.toString(r.sold()-r.beforeSold())));d.put("reason",r.reason());d.put("createdAt",time(r.createdAt()));return d;}
}
