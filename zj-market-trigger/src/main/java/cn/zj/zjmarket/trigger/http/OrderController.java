package cn.zj.zjmarket.trigger.http;
import cn.zj.zjmarket.api.response.ApiResponse;
import cn.zj.zjmarket.domain.identity.model.valobj.AuthenticatedPrincipal;
import cn.zj.zjmarket.domain.order.model.entity.*;
import cn.zj.zjmarket.domain.order.model.valobj.PurchaseConditions;
import cn.zj.zjmarket.domain.order.service.IOrderService;
import cn.zj.zjmarket.domain.product.model.valobj.TrialOffer;
import cn.zj.zjmarket.types.exception.AuthFailure;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.boot.autoconfigure.condition.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.*;
@RestController @RequestMapping("/api/v1")
@ConditionalOnWebApplication(type=ConditionalOnWebApplication.Type.SERVLET)
@ConditionalOnProperty(name="b.order.enabled",havingValue="true")
public final class OrderController {
 private final IOrderService service;public OrderController(IOrderService service){this.service=service;}
 @PostMapping("/purchase-confirmations") ResponseEntity<ApiResponse> confirm(@RequestBody Map<String,Object> b,HttpServletRequest r){String user=actor(r);query(r,Set.of());if(!Set.of("goodsId","mode","teamId","expectedOffer").containsAll(b.keySet())||!b.keySet().containsAll(Set.of("goodsId","mode","expectedOffer")))throw PurchaseConditions.invalid();if(!(b.get("expectedOffer") instanceof Map<?,?> o)||!o.keySet().equals(Set.of("activityId","goodsId","productVersion","originalPrice","deductionPrice","payPrice","currency","targetCount"))||!(o.get("targetCount") instanceof Integer count))throw PurchaseConditions.invalid();var offer=new TrialOffer(text(o,"activityId"),text(o,"goodsId"),text(o,"productVersion"),text(o,"originalPrice"),text(o,"deductionPrice"),text(o,"payPrice"),text(o,"currency"),count);var c=service.confirm(user,new PurchaseConditions(text(b,"goodsId"),text(b,"mode"),b.get("teamId")==null?null:text(b,"teamId"),offer),id(r));return ResponseEntity.status(201).body(ok(confirmation(c),r));}
 @PostMapping("/orders") ResponseEntity<ApiResponse> create(@RequestBody Map<String,Object> b,HttpServletRequest r){String user=actor(r);query(r,Set.of());if(!b.keySet().equals(Set.of("purchaseIntentId","confirmationId")))throw PurchaseConditions.invalid();var result=service.create(user,text(b,"purchaseIntentId"),text(b,"confirmationId"),id(r));return ResponseEntity.status(result.replay()?200:202).body(ok(order(result.order()),r));}
 @GetMapping("/orders") ApiResponse list(HttpServletRequest r){String u=actor(r);query(r,Set.of("page","size"));int page=integer(r,"page",1),size=integer(r,"size",20);return ok(Map.of("items",service.list(u,page,size).stream().map(OrderController::order).toList(),"page",page,"size",size,"total",service.count(u)),r);}
 @GetMapping("/orders/{orderId}") ApiResponse detail(@PathVariable String orderId,HttpServletRequest r){String u=actor(r);query(r,Set.of());return ok(order(service.detail(u,orderId)),r);}
 @GetMapping("/orders/by-intent/{purchaseIntentId}") ApiResponse intent(@PathVariable String purchaseIntentId,HttpServletRequest r){String u=actor(r);query(r,Set.of());return ok(order(service.byIntent(u,purchaseIntentId)),r);}
 @GetMapping("/products/{goodsId}/active-order") ApiResponse active(@PathVariable String goodsId,HttpServletRequest r){String u=actor(r);query(r,Set.of());var o=service.active(u,goodsId);return ok(o==null?null:order(o),r);}
 private static Map<String,Object> confirmation(PurchaseConfirmation c){var q=c.conditions();var m=new LinkedHashMap<String,Object>();m.put("confirmationId",c.confirmationId());m.put("quantity",1);m.put("mode",q.mode());m.put("teamId",q.teamId());m.put("offer",q.expectedOffer());m.put("issuedAt",time(c.issuedAt()));m.put("expiresAt",time(c.expiresAt()));return m;}
 public static Map<String,Object> order(MarketOrder o){
  var c=o.confirmation();var q=c.conditions();var product=new LinkedHashMap<String,Object>();product.put("goodsId",q.goodsId());product.put("productVersion",q.expectedOffer().productVersion());product.put("name",c.goodsName());product.put("imageUrl",c.imageUrl());
  var m=new LinkedHashMap<String,Object>();m.put("orderId",o.orderId());m.put("purchaseIntentId",o.purchaseIntentId());m.put("confirmationId",c.confirmationId());m.put("version",Long.toString(o.orderVersion()));m.put("status",o.businessStatus());m.put("product",product);m.put("offer",q.expectedOffer());m.put("quantity",1);m.put("mode",q.mode());m.put("requestedTeamId",q.teamId());
  for(String key:List.of("aOrderId","teamId","aRecordVersion","aTeamVersion","aOrderStatus","aTeamStatus","paymentDeadline","closedAt","closeBasis","errorCode"))m.put(key,null);
  m.put("createdAt",time(o.createdAt()));m.put("updatedAt",time(o.updatedAt()));m.put("reserveWaitDeadline",time(o.reserveWaitDeadline()));m.put("paymentEnabled",false);m.put("reviewRequired",o.reviewRequired());m.put("canCancel",!o.reviewRequired()&&"NEVER_OPENED".equals(o.paymentExposure())&&Set.of("PROCESSING","WAITING_PAYMENT").contains(o.businessStatus()));m.put("closedAt",o.closedAt()==null?null:time(o.closedAt()));m.put("closeBasis",o.closeBasis());m.put("errorCode",o.errorCode());var a=o.evidence();if(a!=null){m.put("aOrderId",a.orderId());m.put("teamId",a.teamId());m.put("aRecordVersion",a.recordVersion());m.put("aTeamVersion",a.teamVersion());m.put("aOrderStatus",a.orderStatus());m.put("aTeamStatus",a.teamStatus());m.put("paymentDeadline",a.paymentDeadline());}return m;
 }
 private static String actor(HttpServletRequest r){var p=(AuthenticatedPrincipal)r.getAttribute("b.principal");if(p==null)throw new AuthFailure(401,"AUTH_REQUIRED");if(!p.user().roles().contains("USER")&&!p.user().roles().contains("OPERATOR"))throw new AuthFailure(403,"FORBIDDEN");return p.user().userId();}
 private static String text(Map<?,?> b,String key){if(!(b.get(key) instanceof String v))throw PurchaseConditions.invalid();return v;}
 private static void query(HttpServletRequest r,Set<String> allowed){if(r.getParameterMap().entrySet().stream().anyMatch(e->!allowed.contains(e.getKey())||e.getValue().length!=1))throw PurchaseConditions.invalid();}
 private static int integer(HttpServletRequest r,String key,int fallback){String v=r.getParameter(key);if(v==null)return fallback;try{if(!v.matches("[1-9][0-9]{0,9}"))throw PurchaseConditions.invalid();return Integer.parseInt(v);}catch(NumberFormatException e){throw PurchaseConditions.invalid();}}
 private static String time(long ms){return new java.time.format.DateTimeFormatterBuilder().appendInstant(3).toFormatter().format(java.time.Instant.ofEpochMilli(ms));}
 private static String id(HttpServletRequest r){return (String)r.getAttribute("b.requestId");}private static ApiResponse ok(Object d,HttpServletRequest r){return ApiResponse.ok(d,id(r));}
}
