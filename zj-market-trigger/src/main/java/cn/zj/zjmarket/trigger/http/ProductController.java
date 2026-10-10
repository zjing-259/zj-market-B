package cn.zj.zjmarket.trigger.http;

import cn.zj.zjmarket.api.response.ApiResponse;
import cn.zj.zjmarket.domain.identity.model.valobj.AuthenticatedPrincipal;
import cn.zj.zjmarket.domain.product.model.entity.Product;
import cn.zj.zjmarket.domain.product.model.valobj.ProductFields;
import cn.zj.zjmarket.domain.product.model.valobj.ProductView;
import cn.zj.zjmarket.domain.product.model.valobj.SaleStatus;
import cn.zj.zjmarket.domain.product.service.IProductService;
import cn.zj.zjmarket.types.exception.AuthFailure;
import cn.zj.zjmarket.types.exception.ProductFailure;
import jakarta.servlet.http.HttpServletRequest;
import java.util.*;
import org.springframework.boot.autoconfigure.condition.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
@RestController @RequestMapping("/api/v1")
@ConditionalOnWebApplication(type=ConditionalOnWebApplication.Type.SERVLET)
@ConditionalOnProperty(name="b.product.enabled",havingValue="true")
public final class ProductController {
    private final IProductService service;
    private final org.springframework.beans.factory.ObjectProvider<cn.zj.zjmarket.domain.inventory.service.IInventoryService> inventory;
    public ProductController(IProductService service,org.springframework.beans.factory.ObjectProvider<cn.zj.zjmarket.domain.inventory.service.IInventoryService> inventory){this.service=service;this.inventory=inventory;}
    @GetMapping("/products") ApiResponse list(HttpServletRequest req){return page(req,false);}
    @GetMapping("/admin/products") ApiResponse adminList(HttpServletRequest req){return page(req,true);}
    @GetMapping("/products/{id}") ApiResponse detail(@PathVariable String id,HttpServletRequest req){query(req,Set.of());return ok(dto(service.detail(id,false),false),req);}
    @GetMapping("/admin/products/{id}") ApiResponse adminDetail(@PathVariable String id,HttpServletRequest req){operator(req);query(req,Set.of());return ok(dto(service.detail(id,true),true),req);}
    @PostMapping("/admin/products") ResponseEntity<ApiResponse> create(@RequestBody Map<String,Object> body,HttpServletRequest req){
        operator(req);query(req,Set.of());keys(body,false);
        var fields=fields(text(body,"goodsName"),body.containsKey("description")?text(body,"description"):"",image(body),text(body,"originalPrice"),text(body,"currency"),body.containsKey("saleStatus")?text(body,"saleStatus"):"OFF_SALE");
        return ResponseEntity.status(201).body(ok(dto(service.create(fields,requestId(req)),true),req));
    }
    @PutMapping("/admin/products/{id}") ApiResponse edit(@PathVariable String id,@RequestBody Map<String,Object> body,HttpServletRequest req){
        operator(req);query(req,Set.of());keys(body,true);long version;try{version=Product.parseVersion(text(body,"expectedVersion"));}catch(IllegalArgumentException e){throw invalid();}
        var fields=fields(text(body,"goodsName"),text(body,"description"),image(body),text(body,"originalPrice"),text(body,"currency"),text(body,"saleStatus"));return ok(dto(service.edit(id,version,fields,requestId(req)),true),req);
    }
    private static void keys(Map<String,Object> body,boolean edit){var allowed=new HashSet<>(Set.of("goodsName","description","imageUrl","originalPrice","currency","saleStatus"));if(edit)allowed.add("expectedVersion");if(!allowed.containsAll(body.keySet()) || edit && !body.keySet().equals(allowed))throw invalid();}
    private static String text(Map<String,Object> body,String key){if(!(body.get(key) instanceof String v))throw invalid();return v;}
    private static String image(Map<String,Object> body){return body.get("imageUrl")==null?null:text(body,"imageUrl");}
    private ApiResponse page(HttpServletRequest req,boolean admin){if(admin)operator(req);query(req,admin?Set.of("page","size","saleStatus"):Set.of("page","size"));int page=integer(req,"page",1),size=integer(req,"size",20);var result=service.list(page,size,req.getParameter("saleStatus"),admin);return ok(Map.of("items",result.items().stream().map(v -> dto(v,admin)).toList(),"page",result.page(),"size",result.size(),"total",result.total()),req);}
    private static int integer(HttpServletRequest req,String name,int fallback){String v=req.getParameter(name);if(v==null)return fallback;if(!v.matches("[1-9][0-9]{0,9}"))throw invalid();try{return Integer.parseInt(v);}catch(NumberFormatException e){throw invalid();}}
    private static void query(HttpServletRequest req,Set<String> allowed){if(req.getParameterMap().entrySet().stream().anyMatch(e -> !allowed.contains(e.getKey()) || e.getValue().length!=1))throw invalid();}
    private static ProductFields fields(String name,String description,String image,String price,String currency,String status){try{return new ProductFields(name,description,image,price,currency,SaleStatus.valueOf(status));}catch(IllegalArgumentException|NullPointerException e){throw invalid();}}
    private Map<String,Object> dto(ProductView v,boolean admin){var p=v.product();var f=p.fields();var value=new LinkedHashMap<String,Object>();value.put("goodsId",p.goodsId());value.put("goodsName",f.goodsName());value.put("description",f.description());value.put("imageUrl",f.imageUrl());value.put("originalPrice",f.originalPrice().toPlainString());value.put("currency",f.currency());value.put("saleStatus",f.saleStatus().name());value.put("productVersion",Long.toString(p.version()));value.put("syncReady",v.sync().ready(p.version()));if(admin)value.put("sync",v.sync());var stock=inventory.getIfAvailable();if(stock!=null)value.put("availability",stock.detail(p.goodsId()).available()>0?"IN_STOCK":"OUT_OF_STOCK");return value;}
    // Check the authenticated principal at the handler too: raw URI spellings cannot bypass role checks.
    private static void operator(HttpServletRequest req){var p=(AuthenticatedPrincipal)req.getAttribute("b.principal");if(p==null)throw new AuthFailure(401,"AUTH_REQUIRED");if(!p.user().roles().contains("OPERATOR"))throw new AuthFailure(403,"FORBIDDEN");}
    private static ProductFailure invalid(){return new ProductFailure(400,"VALIDATION_FAILED");}
    private static String requestId(HttpServletRequest req){return (String)req.getAttribute("b.requestId");}
    private static ApiResponse ok(Object data,HttpServletRequest req){return ApiResponse.ok(data,requestId(req));}
}
