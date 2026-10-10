package cn.zj.zjmarket.verification;

import cn.zj.zjmarket.ZjMarketApplication;
import cn.zj.zjmarket.domain.identity.service.IIdentityService;
import cn.zj.zjmarket.domain.product.adapter.port.IProductEventPort;
import cn.zj.zjmarket.domain.product.adapter.repository.IProductRepository;
import cn.zj.zjmarket.domain.product.model.valobj.ProductFields;
import cn.zj.zjmarket.domain.product.model.valobj.SaleStatus;
import cn.zj.zjmarket.domain.product.service.IProductService;
import cn.zj.zjmarket.domain.product.service.impl.ProductService;
import cn.zj.zjmarket.types.exception.ProductFailure;
import com.fasterxml.jackson.databind.*;
import java.net.*;
import java.net.http.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import javax.sql.DataSource;
import org.springframework.boot.*;
import org.springframework.boot.web.server.context.WebServerApplicationContext;
/** Actual B HTTP / MySQL acceptance, exclusively the isolated B-02 database. */
public final class ProductCommands {
    private static final ObjectMapper JSON=new ObjectMapper();
    public static int run(){
        try {
            if(!"b02-test".equals(env("B_DATABASE_SCOPE")) || !env("B_DATABASE_URL").matches("^jdbc:mysql://[^/]+/zj_market_b02_test(?:\\?.*)?$") || !"zj_market_b02_test_app".equals(env("B_DATABASE_USERNAME")))throw new IllegalArgumentException("Exact B test database required");
            var app=new SpringApplication(ZjMarketApplication.class);
            try(var ctx=app.run("--server.port=0","--b.order.enabled=false","--b.trade.enabled=false","--b.identity.enabled=true","--b.product.enabled=true","--b.infrastructure.database.enabled=true","--b.trial.enabled=false","--b.sync.enabled=false","--b.infrastructure.rpc.enabled=false","--b.infrastructure.mq.enabled=false")){
                var evidence=new ArrayList<String>();var db=ctx.getBean(DataSource.class);var products=ctx.getBean(IProductService.class);var store=ctx.getBean(IProductRepository.class);var events=ctx.getBean(IProductEventPort.class);
                var identity=ctx.getBean(IIdentityService.class);String suffix=UUID.randomUUID().toString().replace("-","").substring(0,16),password="Product-"+UUID.randomUUID();
                identity.register("u"+suffix,password,"test user");identity.initializeOperator("o"+suffix,password,"test operator");
                var http=new Client("http://127.0.0.1:"+((WebServerApplicationContext)ctx).getWebServer().getPort(),env("B_IDENTITY_ORIGIN"));
                String user=http.login("u"+suffix,password),op=http.login("o"+suffix,password);
                var draft=new LinkedHashMap<String,Object>();draft.put("goodsName","  商品 "+suffix+"  ");draft.put("originalPrice","123.45");draft.put("currency","CNY");
                http.call("POST","/admin/products",draft,null,401);http.call("POST","/admin/products",draft,user,403);http.call("GET","/admin/products",null,user,403);
                http.call("POST","/%61dmin/products",draft,null,401);http.call("POST","/%61dmin/products",draft,user,403);http.call("GET","/%61dmin/products",null,user,403);
                var created=http.call("POST","/admin/products",draft,op,201).path("data");String id=created.path("goodsId").asText();
                check(created.path("productVersion").asText().equals("1") && created.path("saleStatus").asText().equals("OFF_SALE") && created.path("description").asText().isEmpty() && created.path("imageUrl").isNull(),"creation defaults");
                check(created.path("goodsName").asText().equals("商品 "+suffix),"name strip");check(created.path("sync").path("state").asText().equals("PENDING") && !created.path("syncReady").asBoolean(),"pending not confirmed");
                http.call("GET","/admin/products/"+id.toUpperCase(java.util.Locale.ROOT),null,op,404);
                http.call("GET","/products/"+id,null,null,404);http.call("GET","/products",null,null,200);
                // A uses String.length: supplementary characters take two UTF-16 units.
                for(String valid:List.of("商".repeat(128),"🛍".repeat(64),"a".repeat(126)+"🛍")){
                    var body=new LinkedHashMap<String,Object>(draft);body.put("goodsName","  "+valid+"  ");
                    var boundary=http.call("POST","/admin/products",body,op,201).path("data");String boundaryId=boundary.path("goodsId").asText();
                    check(boundary.path("goodsName").asText().equals(valid) && valid.length()==128,"UTF16 128 create and normalization");
                    check(http.call("GET","/admin/products/"+boundaryId,null,op,200).path("data").path("goodsName").asText().equals(valid),"UTF16 name database roundtrip");
                    var boundaryEdit=edit(boundary);boundaryEdit.put("goodsName","b".repeat(126)+"🛍");
                    var changed=http.call("PUT","/admin/products/"+boundaryId,boundaryEdit,op,200).path("data");
                    check(changed.path("productVersion").asText().equals("2"),"UTF16 128 edit");
                    for(String invalidName:List.of("a".repeat(129),"🛍".repeat(65),"a".repeat(127)+"🛍")){
                        var invalidCreate=new LinkedHashMap<String,Object>(draft);invalidCreate.put("goodsName",invalidName);http.call("POST","/admin/products",invalidCreate,op,400);
                        var invalidEdit=edit(changed);invalidEdit.put("goodsName",invalidName);http.call("PUT","/admin/products/"+boundaryId,invalidEdit,op,400);
                    }
                    check(count(db,boundaryId)==2 && products.detail(boundaryId,true).product().version()==2,"rejected name leaves product/event unchanged");
                    try(var c=db.getConnection();var q=c.prepareStatement("SELECT body FROM b_product_outbox WHERE goods_id=? AND product_version=1")){q.setString(1,boundaryId);try(var rows=q.executeQuery()){check(rows.next() && JSON.readTree(rows.getString(1)).path("payload").path("goodsName").asText().equals(valid),"UTF16 name exact A snapshot");}}
                }
                for(String price:List.of("0.00","1.001","1","1000000.00","-1.00","01.00")){var bad=new LinkedHashMap<>(draft);bad.put("originalPrice",price);http.call("POST","/admin/products",bad,op,400);}
                for(var bad:List.of(Map.of("originalPrice",123.45),Map.of("currency","USD"),Map.of("description","<script>alert(1)</script>"),Map.of("imageUrl","http://example.test/x"),Map.of("imageUrl","https://user:pass@example.test/x"),Map.of("goodsName"," "),Map.of("goodsId","spoof"))){var body=new LinkedHashMap<String,Object>(draft);body.putAll(bad);http.call("POST","/admin/products",body,op,400);}
                http.call("GET","/products?page=0",null,null,400);http.call("GET","/products?size=101",null,null,400);http.call("GET","/products?page=1&page=2",null,null,400);http.call("GET","/products?saleStatus=OFF_SALE",null,null,400);
                var edit=edit(created);edit.put("saleStatus","ON_SALE");var online=http.call("PUT","/admin/products/"+id,edit,op,200).path("data");check(online.path("productVersion").asText().equals("2"),"on sale version");
                http.call("GET","/products/"+id,null,null,200);check(contains(http.call("GET","/products?size=100",null,null,200),id),"public on sale list");
                http.call("PUT","/admin/products/"+id,edit,op,409);
                edit=edit(online);long count=count(db,id);var unchanged=http.call("PUT","/admin/products/"+id,edit,op,200).path("data");check(unchanged.path("productVersion").asText().equals("2") && count==count(db,id),"no-op no event");
                edit.put("description","原文\n  保留空白\n2 < 3");edit.put("imageUrl","https://example.test/product.png");var decorated=http.call("PUT","/admin/products/"+id,edit,op,200).path("data");check(decorated.path("productVersion").asText().equals("3"),"description/image version");
                check(decorated.path("description").asText().equals(edit.get("description")),"description unchanged");
                // Race at the same expected version: lock+version comparison yields one commit.
                var first=edit(decorated);var second=edit(decorated);first.put("goodsName","editor one");second.put("goodsName","editor two");
                try(var executor=Executors.newVirtualThreadPerTaskExecutor()){
                    var a=executor.submit(() -> http.send("PUT","/admin/products/"+id,first,op));var b=executor.submit(() -> http.send("PUT","/admin/products/"+id,second,op));
                    check(Set.of(a.get().statusCode(),b.get().statusCode()).equals(Set.of(200,409)),"concurrent one winner");
                }
                var winner=http.call("GET","/admin/products/"+id,null,op,200).path("data");check(winner.path("productVersion").asText().equals("4") && count(db,id)==4,"one increment one event");
                var missing=edit(winner);missing.remove("imageUrl");http.call("PUT","/admin/products/"+id,missing,op,400);
                for(Object version:List.of("04","0","9223372036854775808",4)){var bad=edit(winner);bad.put("expectedVersion",version);http.call("PUT","/admin/products/"+id,bad,op,400);}
                // Exact immutable A wire fact, all historical versions remain distinct.
                try(var c=db.getConnection();var p=c.prepareStatement("SELECT body FROM b_product_outbox WHERE goods_id=? ORDER BY product_version")){p.setString(1,id);try(var rows=p.executeQuery()){
                    int v=0;while(rows.next()){var body=JSON.readTree(rows.getString(1));v++;var payload=body.path("payload");check(payload.path("productVersion").asText().equals(Integer.toString(v)),"historic immutable version");check(payload.size()==6 && !payload.has("description") && !payload.has("imageUrl"),"A payload exactly six fields");
                    check(body.size()==9 && body.path("eventType").asText().equals("PRODUCT_SNAPSHOT_CHANGED") && body.path("schemaVersion").asInt()==1 && body.path("producer").asText().equals(env("B_PRODUCT_EVENT_PRODUCER")) && body.path("source").asText().equals(env("B_PRODUCT_EVENT_SOURCE")) && body.path("channel").asText().equals(env("B_PRODUCT_EVENT_CHANNEL")),"complete envelope");
                    check(body.path("occurredAt").asText().matches(".*\\.[0-9]{3}Z") && !body.path("correlationId").asText().isBlank(),"commit timestamp and request correlation");
                    if(v==1)check(payload.path("goodsName").asText().equals(created.path("goodsName").asText()) && payload.path("saleStatus").asText().equals("OFF_SALE"),"old body not recomputed");
                    if(v==3)check(payload.path("goodsName").asText().equals(created.path("goodsName").asText()),"display only edit snapshot increments");}
                    check(v==4,"all facts saved");}}
                var next=new ProductFields("rollback", "", null, "9.99", "CNY",SaleStatus.ON_SALE);
                for(String failPoint:List.of("appendEvent","target")){
                    IProductRepository failing=(IProductRepository)java.lang.reflect.Proxy.newProxyInstance(IProductRepository.class.getClassLoader(),new Class[]{IProductRepository.class},(proxy,method,args) -> {
                        try{Object value=method.invoke(store,args);if(method.getName().equals(failPoint))throw new ProductFailure(503,"DEPENDENCY_UNAVAILABLE");return value;}catch(java.lang.reflect.InvocationTargetException e){throw e.getCause();}
                    });
                    var service=new ProductService(failing,events,java.time.Clock.systemUTC());
                    try{service.edit(id,4,next,"rollback-test");throw new IllegalStateException("check: expected rollback");}catch(ProductFailure expected){check(expected.status()==503,"fault injection status");}
                    check(products.detail(id,true).product().version()==4 && count(db,id)==4 && products.detail(id,true).sync().targetVersion().equals("4"),"product event sync all rollback after "+failPoint);
                    long before=store.count(null);try{service.create(next,"rollback-create");throw new IllegalStateException("check: expected create rollback");}catch(ProductFailure expected){check(expected.status()==503,"create fault");}check(store.count(null)==before,"failed creation rolled back");
                }
                edit=edit(winner);edit.put("saleStatus","OFF_SALE");http.call("PUT","/admin/products/"+id,edit,op,200);http.call("GET","/products/"+id,null,null,404);check(!contains(http.call("GET","/products?size=100",null,null,200),id),"off sale hidden immediately");http.call("GET","/admin/products/"+id,null,op,200);
                http.call("DELETE","/admin/products/"+id,null,op,405);http.call("GET","/admin/products?saleStatus=UNKNOWN",null,op,400);
                // Actual BIGINT > JS safe integer and exhaustion do not lose precision or wrap.
                try(var c=db.getConnection();var p=c.prepareStatement("UPDATE b_product SET product_version=9223372036854775807 WHERE goods_id=?")){p.setString(1,id);p.executeUpdate();}
                try(var c=db.getConnection();var p=c.prepareStatement("UPDATE b_product_sync SET target_version=9223372036854775807 WHERE goods_id=?")){p.setString(1,id);p.executeUpdate();}
                try {
                var maximum=http.call("GET","/admin/products/"+id,null,op,200).path("data");check(maximum.path("productVersion").isTextual() && maximum.path("productVersion").asText().equals("9223372036854775807"),"BIGINT string precision");
                var exhausted=edit(maximum);exhausted.put("goodsName","cannot wrap");var error=http.call("PUT","/admin/products/"+id,exhausted,op,409);check(error.path("code").asText().equals("PRODUCT_VERSION_EXHAUSTED"),"exhaustion code");
                } finally {
                // Restore owned fixture consistency after boundary probe (no A or development data).
                try(var c=db.getConnection();var p=c.prepareStatement("UPDATE b_product SET product_version=5 WHERE goods_id=?")){p.setString(1,id);p.executeUpdate();}
                try(var c=db.getConnection();var p=c.prepareStatement("UPDATE b_product_sync SET target_version=5 WHERE goods_id=?")){p.setString(1,id);p.executeUpdate();}
                }
                ((com.zaxxer.hikari.HikariDataSource)db).close();http.call("GET","/products",null,null,503);
                evidence.add("java="+Runtime.version());evidence.add("springBoot="+SpringBootVersion.getVersion());
                evidence.add("HTTP=6 product operations;anonymous/USER/OPERATOR permissions=PASSED");evidence.add("validation=UTF16-128-create/edit/emoji/mixed/overflow-no-write/name-strip/plain-description/HTML/HTTPS/money/currency/strict-types/complete-PUT/pagination=PASSED");
                evidence.add("versions=create1/no-op/display-edit/concurrent-CAS/precision/exhaustion=PASSED");evidence.add("immutable-contract=9 envelope fields/6 payload fields/requestId/millisecond-UTC/history=PASSED");
                evidence.add("transaction=product+outbox+sync rollback after outbox and target writes; create/edit=PASSED");evidence.add("OFF_SALE immediate local visibility/A RPC and MQ disabled=PASSED");evidence.add("database-unavailable=503;status=PASSED");
                Path report=Path.of(env("B_PRODUCT_REPORT"));Files.createDirectories(report.toAbsolutePath().getParent());Files.write(report,evidence);System.out.println("B product actual HTTP/MySQL verification: PASSED");
            }return 0;
        }catch(Exception e){System.err.println("B product verification failed: "+e.getClass().getSimpleName()+" "+(e.getMessage()!=null && e.getMessage().startsWith("check:")?e.getMessage():"details withheld"));return 1;}
    }
    static Map<String,Object> edit(JsonNode p){var result=new LinkedHashMap<String,Object>();for(String k:List.of("goodsName","description","originalPrice","currency","saleStatus"))result.put(k,p.path(k).asText());result.put("imageUrl",p.path("imageUrl").isNull()?null:p.path("imageUrl").asText());result.put("expectedVersion",p.path("productVersion").asText());return result;}
    static boolean contains(JsonNode body,String id){for(var item:body.path("data").path("items"))if(item.path("goodsId").asText().equals(id))return true;return false;}
    static long count(DataSource db,String id)throws Exception{try(var c=db.getConnection();var p=c.prepareStatement("SELECT COUNT(*) FROM b_product_outbox WHERE goods_id=?")){p.setString(1,id);try(var rows=p.executeQuery()){rows.next();return rows.getLong(1);}}}
    static String env(String key){String value=System.getenv(key);if(value==null || value.isBlank())throw new IllegalArgumentException("Missing "+key);return value;}
    static void check(boolean value,String name){if(!value)throw new IllegalStateException("check: "+name);}
    static final class Client {
        final String base,origin;final CookieManager cookies=new CookieManager(null,CookiePolicy.ACCEPT_ALL);final HttpClient http;
        Client(String base,String origin){this.base=base;this.origin=origin;http=HttpClient.newBuilder().cookieHandler(cookies).connectTimeout(java.time.Duration.ofSeconds(5)).build();}
        HttpResponse<String> send(String method,String path,Object body,String jwt)throws Exception{
            var builder=HttpRequest.newBuilder(URI.create(base+"/api/v1"+path)).timeout(java.time.Duration.ofSeconds(20));if(jwt!=null)builder.header("Authorization","Bearer "+jwt);
            if(body!=null)builder.header("Content-Type","application/json");builder.method(method,body==null?HttpRequest.BodyPublishers.noBody():HttpRequest.BodyPublishers.ofString(JSON.writeValueAsString(body)));return http.send(builder.build(),HttpResponse.BodyHandlers.ofString());
        }
        JsonNode call(String method,String path,Object body,String jwt,int status)throws Exception{var response=send(method,path,body,jwt);check(response.statusCode()==status,"HTTP "+path+" "+response.statusCode()+" expected "+status);var result=JSON.readTree(response.body());check(response.headers().firstValue("X-Request-Id").orElse("").equals(result.path("requestId").asText()),"requestId");return result;}
        String login(String login,String password)throws Exception{
            String csrf=call("GET","/auth/csrf",null,null,200).path("data").path("token").asText();var request=HttpRequest.newBuilder(URI.create(base+"/api/v1/auth/login")).header("Content-Type","application/json").header("Origin",origin).header("X-CSRF-TOKEN",csrf).POST(HttpRequest.BodyPublishers.ofString(JSON.writeValueAsString(Map.of("loginName",login,"password",password)))).build();var response=http.send(request,HttpResponse.BodyHandlers.ofString());check(response.statusCode()==200,"login");return JSON.readTree(response.body()).path("data").path("accessToken").asText();
        }
    }
}
