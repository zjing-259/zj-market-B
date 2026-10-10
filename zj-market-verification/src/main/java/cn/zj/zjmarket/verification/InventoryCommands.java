package cn.zj.zjmarket.verification;
import cn.zj.zjmarket.ZjMarketApplication;
import cn.zj.zjmarket.domain.identity.service.IIdentityService;
import cn.zj.zjmarket.domain.product.service.IProductService;
import cn.zj.zjmarket.domain.product.model.valobj.*;
import cn.zj.zjmarket.domain.inventory.service.IInventoryService;
import cn.zj.zjmarket.domain.inventory.model.valobj.*;
import com.fasterxml.jackson.databind.*;
import java.util.*;
import java.util.concurrent.*;
import java.nio.file.*;
import javax.sql.DataSource;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.web.server.context.WebServerApplicationContext;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import static cn.zj.zjmarket.verification.ProductCommands.*;
/** Real B HTTP/MySQL acceptance, restricted to the existing isolated B schema. */
public final class InventoryCommands {
 public static int run(){
  try{
   if(!"b02-test".equals(env("B_DATABASE_SCOPE")) || !env("B_DATABASE_URL").matches("^jdbc:mysql://[^/]+/zj_market_b02_test(?:\\\\?.*)?$") || !"zj_market_b02_test_app".equals(env("B_DATABASE_USERNAME")))throw new IllegalArgumentException("Exact isolated database required");
   try(var ctx=new SpringApplication(ZjMarketApplication.class).run("--server.port=0","--b.order.enabled=false","--b.trade.enabled=false","--b.identity.enabled=true","--b.product.enabled=true","--b.inventory.enabled=true","--b.trial.enabled=false","--b.sync.enabled=false","--b.infrastructure.database.enabled=true","--b.infrastructure.rpc.enabled=false","--b.infrastructure.mq.enabled=false")){
    var db=ctx.getBean(DataSource.class);var identity=ctx.getBean(IIdentityService.class);var products=ctx.getBean(IProductService.class);var inventory=ctx.getBean(IInventoryService.class);
    String suffix=UUID.randomUUID().toString().replace("-","").substring(0,16),password="Inventory-"+UUID.randomUUID();
    var u=identity.register("u"+suffix,password,"库存验收用户");
    var a=identity.initializeOperator("a"+suffix,password,"库存运营一");var b=identity.initializeOperator("b"+suffix,password,"库存运营二");
    var http=new Client("http://127.0.0.1:"+((WebServerApplicationContext)ctx).getWebServer().getPort(),env("B_IDENTITY_ORIGIN"));
    String user=http.login("u"+suffix,password),op=http.login("a"+suffix,password),other=http.login("b"+suffix,password);
    var fields=new ProductFields("库存验收 "+suffix,"",null,"10.00","CNY",SaleStatus.OFF_SALE);
    String id=products.create(fields,"inventory-create").product().goodsId(),second=products.create(fields,"inventory-create-2").product().goodsId();
    try(var c=db.getConnection();var q=c.createStatement();var rows=q.executeQuery("SELECT (SELECT COUNT(*) FROM b_product p LEFT JOIN b_inventory_account a ON a.goods_id=p.goods_id WHERE a.goods_id IS NULL)+(SELECT COUNT(*) FROM b_inventory_operation WHERE request_hash<>SHA2(CONCAT_WS(CHAR(10),operator_id,kind,goods_id,CAST(delta AS CHAR),CAST(expected_version AS CHAR),reason),256))")){rows.next();check(rows.getLong(1)==0,"account completeness and canonical audit backfill");}
    String root="/admin/inventory/",key=UUID.randomUUID().toString();
    http.call("GET",root+"missing",null,op,404);
    check(inventory.detail(id).available()==0 && inventory.detail(id).version()==1,"new product zero account");
    for(String path:List.of("/admin/inventory",root+id,root+id+"/ledger",root+"operations/"+key)){
     http.call("GET",path,null,null,401);http.call("GET",path,null,user,403);
    }
    http.call("POST",root+id+"/inbounds",input(key,"quantity","100","1"),null,401);
    http.call("POST",root+id+"/inbounds",input(key,"quantity","100","1"),user,403);
    var first=http.call("POST",root+id+"/inbounds",input(key,"quantity","100","1"),op,201).path("data");
    check(first.path("outcome").asText().equals("SUCCEEDED") && inventory.detail(id).available()==100,"off-sale inbound");
    var replay=http.call("POST",root+id+"/inbounds",input(key,"quantity","100","1"),op,200).path("data");
    check(first.equals(replay),"immutable success replay before old version");
    check(http.call("GET",root+"operations/"+key,null,op,200).path("data").equals(first),"result query same snapshot");
    http.call("GET",root+"operations/"+key,null,other,404);http.call("GET",root+"operations/missing",null,op,404);
    http.call("POST",root+id+"/inbounds",input(key,"quantity","101","1"),op,409);
    http.call("POST",root+second+"/inbounds",input(key,"quantity","100","1"),op,409);
    check(inventory.detail(second).available()==0,"same-key different SKU no write");
    String rejected=UUID.randomUUID().toString();
    var reject=http.call("POST",root+id+"/adjustments",input(rejected,"delta","-101","2"),op,409).path("data").path("inventoryOperation");
    check(reject.path("outcome").asText().equals("REJECTED") && reject.path("code").asText().equals("STOCK_INSUFFICIENT"),"durable insufficient rejection");
    check(http.call("GET",root+"operations/"+rejected,null,op,200).path("data").equals(reject),"query rejection");
    http.call("POST",root+id+"/adjustments",input(rejected,"delta","-101","2"),op,409);
    check(inventory.detail(id).available()==100 && inventory.ledger(id,1,100).total()==1,"rejection no balance/version/ledger");
    http.call("POST",root+id+"/adjustments",input(UUID.randomUUID().toString(),"delta","-1","1"),op,409);
    for(String invalid:List.of("0","01","1.5","+1","9223372036854775808")){
     http.call("POST",root+id+"/inbounds",input(UUID.randomUUID().toString(),"quantity",invalid,"2"),op,400);
    }
    var spoof=input(UUID.randomUUID().toString(),"quantity","1","2");spoof.put("userId",a.userId());http.call("POST",root+id+"/inbounds",spoof,op,400);
    http.call("GET","/admin/inventory?page=0",null,op,400);http.call("GET","/admin/inventory?size=101",null,op,400);
    // Same expected version: exactly one mutation, one committed rejection.
    try(var pool=Executors.newVirtualThreadPerTaskExecutor()){
     var x=pool.submit(() -> http.send("POST",root+id+"/adjustments",input(UUID.randomUUID().toString(),"delta","-1","2"),op));
     var y=pool.submit(() -> http.send("POST",root+id+"/adjustments",input(UUID.randomUUID().toString(),"delta","-1","2"),other));
     check(new HashSet<>(List.of(x.get().statusCode(),y.get().statusCode())).equals(Set.of(201,409)),"version lock race");
    }
    check(inventory.detail(id).available()==99 && inventory.detail(id).version()==3,"concurrent single mutation");
    String same=UUID.randomUUID().toString();
    try(var pool=Executors.newVirtualThreadPerTaskExecutor()){
     var x=pool.submit(() -> http.send("POST",root+id+"/inbounds",input(same,"quantity","1","3"),op));
     var y=pool.submit(() -> http.send("POST",root+id+"/inbounds",input(same,"quantity","1","3"),op));
     check(new HashSet<>(List.of(x.get().statusCode(),y.get().statusCode())).equals(Set.of(201,200)),"same-key concurrent replay");
    }
    // Cross-SKU same key races on unique(operator,key), without leaving a loser balance.
    String cross=UUID.randomUUID().toString();long vi=inventory.detail(id).version();
    try(var pool=Executors.newVirtualThreadPerTaskExecutor()){
     var x=pool.submit(() -> http.send("POST",root+id+"/inbounds",input(cross,"quantity","2",Long.toString(vi)),op));
     var y=pool.submit(() -> http.send("POST",root+second+"/inbounds",input(cross,"quantity","2","1"),op));
     check(new HashSet<>(List.of(x.get().statusCode(),y.get().statusCode())).equals(Set.of(201,409)),"cross-SKU unique race");
    }
    // Throw after actual writes, verifying account + operation + ledger roll back together.
    var tx=new TransactionTemplate(new DataSourceTransactionManager(db));String rollback=UUID.randomUUID().toString();long before=inventory.detail(id).available(),version=inventory.detail(id).version(),ledgers=inventory.ledger(id,1,100).total();
    try{tx.execute(s -> {inventory.execute(a.userId(),rollback,new InventoryRequest("INBOUND",id,7,version,"rollback probe"));throw new IllegalStateException("owned rollback probe");});}catch(IllegalStateException expected){}
    check(inventory.detail(id).available()==before && inventory.ledger(id,1,100).total()==ledgers,"atomic rollback balance and ledger");
    http.call("GET",root+"operations/"+rollback,null,op,404);
    final String[] failedProduct={null};
    try{tx.execute(s -> {failedProduct[0]=products.create(fields,"inventory-rollback").product().goodsId();throw new IllegalStateException("owned product rollback");});}catch(IllegalStateException expected){}
    try(var c=db.getConnection();var q=c.prepareStatement("SELECT (SELECT COUNT(*) FROM b_product WHERE goods_id=?)+(SELECT COUNT(*) FROM b_inventory_account WHERE goods_id=?)+(SELECT COUNT(*) FROM b_product_outbox WHERE goods_id=?)")){
     q.setString(1,failedProduct[0]);q.setString(2,failedProduct[0]);q.setString(3,failedProduct[0]);try(var rows=q.executeQuery()){rows.next();check(rows.getLong(1)==0,"product account outbox rollback");}
    }
    String large=products.create(fields,"large").product().goodsId();
    http.call("POST",root+large+"/inbounds",input(UUID.randomUUID().toString(),"quantity",Long.toString(Long.MAX_VALUE),"1"),op,201);
    check(http.call("GET",root+large,null,op,200).path("data").path("available").asText().equals(Long.toString(Long.MAX_VALUE)),"BIGINT exact string");
    var overflow=http.call("POST",root+large+"/inbounds",input(UUID.randomUUID().toString(),"quantity","1","2"),op,409);
    check(overflow.path("code").asText().equals("INVENTORY_QUANTITY_OVERFLOW"),"overflow rejection");
    http.call("POST",root+large+"/adjustments",input(UUID.randomUUID().toString(),"delta",Long.toString(-Long.MAX_VALUE),"2"),op,201);
    // Public availability stays boolean-like and excludes exact inventory counts.
    var old=products.detail(id,true);products.edit(id,old.product().version(),new ProductFields(fields.goodsName(),"",null,"10.00","CNY",SaleStatus.ON_SALE),"on-sale");
    var publicView=http.call("GET","/products/"+id,null,null,200).path("data");
    check(publicView.path("availability").asText().equals("IN_STOCK") && !publicView.has("available") && !publicView.has("reserved") && !publicView.has("sold"),"public inventory privacy");
    var all=inventory.ledger(id,1,100);long sum=all.items().stream().mapToLong(InventoryLedger::delta).sum();
    check(sum==inventory.detail(id).available(),"ledger reconciles account");
    ((com.zaxxer.hikari.HikariDataSource)db).close();http.call("GET",root+id,null,op,503);
    Files.createDirectories(Path.of(env("B_INVENTORY_REPORT")).toAbsolutePath().getParent());
    Files.write(Path.of(env("B_INVENTORY_REPORT")),List.of("status=PASSED","java="+Runtime.version(),"HTTP=inventory 6 operations; permissions/user isolation/strict inputs=PASSED","D28-D32=off-sale/inbound/result-query/durable-rejection/original-key-replay=PASSED","MySQL=version race/same-key race/cross-SKU race/atomic rollback/BIGINT overflow/ledger reconciliation=PASSED","product=zero-account + product/outbox rollback/public availability privacy=PASSED","database outage=503"));
    System.out.println("B inventory actual HTTP/MySQL acceptance: PASSED");
   }return 0;
  }catch(Exception e){System.err.println("B inventory acceptance failed: "+e.getClass().getSimpleName()+" "+(e.getMessage()!=null&&e.getMessage().startsWith("check:")?e.getMessage():"details withheld"));return 1;}
 }
 private static Map<String,Object> input(String id,String field,String value,String version){var m=new LinkedHashMap<String,Object>();m.put("operationId",id);m.put(field,value);m.put("expectedVersion",version);m.put("reason","库存验收");return m;}
}
