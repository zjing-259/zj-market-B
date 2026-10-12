import java.nio.file.*;
import java.sql.*;
import java.util.*;
import org.flywaydb.core.Flyway;
import cn.zj.zjmarket.ZjMarketApplication;
import cn.zj.zjmarket.domain.identity.service.IIdentityService;
import cn.zj.zjmarket.domain.identity.adapter.repository.IIdentityRepository;
import cn.zj.zjmarket.domain.identity.adapter.port.IPasswordPort;
import cn.zj.zjmarket.domain.product.service.IProductService;
import cn.zj.zjmarket.domain.product.model.valobj.*;
import cn.zj.zjmarket.domain.inventory.service.IInventoryService;
import cn.zj.zjmarket.domain.inventory.model.valobj.InventoryRequest;
import org.springframework.boot.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import javax.sql.DataSource;
/** Explicit deployment-only maintenance. Never copied into runtime images. */
public final class DeploymentTool {
 static Properties p=new Properties();
 static void require(boolean ok,String reason){if(!ok)throw new IllegalStateException(reason);}
 static Connection db(String who)throws Exception{return DriverManager.getConnection(p.getProperty(who+".url"),p.getProperty(who+".user"),p.getProperty(who+".password"));}
 static String hash(String text)throws Exception{return HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(text.getBytes(java.nio.charset.StandardCharsets.UTF_8)));}
 static List<String> statements(String sql){
  List<String> result=new ArrayList<>();StringBuilder current=new StringBuilder();char quote=0;
  for(int i=0;i<sql.length();i++){char ch=sql.charAt(i);current.append(ch);
   if(quote!=0){if(ch==92 && i+1<sql.length()){current.append(sql.charAt(++i));continue;}if(ch==quote){if(i+1<sql.length()&&sql.charAt(i+1)==quote){current.append(sql.charAt(++i));}else quote=0;}}
   else if(ch==39||ch==34||ch==96)quote=ch;
   else if(ch==';'){current.setLength(current.length()-1);result.add(current.toString());current.setLength(0);}
  }
  require(quote==0,"Unterminated SQL literal");if(!current.toString().isBlank())result.add(current.toString());return result;
 }
 static void aInit()throws Exception {
  try(Connection c=db("a_migrator")){
   var s=c.createStatement();var lock=s.executeQuery("SELECT GET_LOCK('b06_a_init',0)");lock.next();require(lock.getInt(1)==1,"Initialization already active");
   s.execute("CREATE TABLE IF NOT EXISTS b06_init_journal(step INT PRIMARY KEY, input_hash CHAR(64) NOT NULL, state VARCHAR(16) NOT NULL)");
   String sql=Files.readString(Path.of("/input/a-empty-schema.sql")).replaceAll("(?m)^--.*$","");int step=0;
   for(String raw:statements(sql)){String statement=raw.trim();if(statement.isEmpty())continue;step++;String digest=hash(statement);
    var find=c.prepareStatement("SELECT input_hash,state FROM b06_init_journal WHERE step=?");find.setInt(1,step);var rs=find.executeQuery();
    if(rs.next()){require(digest.equals(rs.getString(1)) && "APPLIED".equals(rs.getString(2)),"DDL interrupted or input changed; manual audit required");continue;}
    var mark=c.prepareStatement("INSERT INTO b06_init_journal VALUES (?,?,'PREPARED')");mark.setInt(1,step);mark.setString(2,digest);mark.executeUpdate();
    s.execute(statement);s.executeUpdate("UPDATE b06_init_journal SET state='APPLIED' WHERE step="+step);
   }
   var pk=s.executeQuery("SELECT GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) FROM information_schema.statistics WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='ab_waiting_dependency' AND INDEX_NAME='PRIMARY'");pk.next();require("consumer,producer,event_id".equals(pk.getString(1)),"Waiting identity key mismatch");
  }
 }
 static void migrate(){Flyway f=Flyway.configure().dataSource(p.getProperty("b_migrator.url"),p.getProperty("b_migrator.user"),p.getProperty("b_migrator.password")).schemas("zj_market_b06").defaultSchema("zj_market_b06").createSchemas(false).cleanDisabled(true).baselineOnMigrate(false).locations("classpath:db/migration").load();f.migrate();f.validate();require("18".equals(f.info().current().getVersion().getVersion()),"Expected V18");}
 static void denied(Connection c,String sql)throws Exception {try{c.createStatement().execute(sql);}catch(SQLException e){require((e.getErrorCode()==1142||e.getErrorCode()==1044)&&e.getSQLState().startsWith("42"),"Unexpected denial");return;}throw new IllegalStateException("Permission unexpectedly allowed");}
 static void verify()throws Exception {
  for(String who:List.of("a_runtime","b_runtime"))try(Connection c=db(who)){
   String schema=who.equals("a_runtime")?"group_buy_market_b06":"zj_market_b06",other=who.equals("a_runtime")?"zj_market_b06":"group_buy_market_b06";
   var s=c.createStatement();var id=s.executeQuery("SELECT DATABASE(),CURRENT_USER()");id.next();require(schema.equals(id.getString(1))&&id.getString(2).equals(who+"@%"),"Wrong database/account");
   var tls=s.executeQuery("SHOW SESSION STATUS LIKE 'Ssl_cipher'");tls.next();require(!tls.getString(2).isBlank(),"Unencrypted runtime session");
   Set<String> expected=new HashSet<>(Files.readAllLines(Path.of("/input/"+who+"-tables.txt")));Set<String> actual=new HashSet<>();
   var grants=s.executeQuery("SHOW GRANTS");while(grants.next()){String g=grants.getString(1);if(g.startsWith("GRANT USAGE ON *.* TO "))continue;
    String prefix="GRANT SELECT, INSERT, UPDATE, DELETE ON `"+schema+"`.`";require(g.startsWith(prefix)&&!g.contains("WITH GRANT OPTION"),"Unexpected runtime privilege");actual.add(g.substring(prefix.length(),g.indexOf("` TO ")));}
   require(expected.equals(actual),"Runtime table grants mismatch");
   for(String t:expected)s.executeQuery("SELECT * FROM `"+t+"` LIMIT 0").close();
   c.setAutoCommit(false);
   try{
    String key=UUID.randomUUID().toString();
    if(who.equals("b_runtime")){
     var insert=c.prepareStatement("INSERT INTO b_database_probe VALUES (?,?)");insert.setString(1,key);insert.setString(2,"initial");require(insert.executeUpdate()==1,"Runtime INSERT");
     var update=c.prepareStatement("UPDATE b_database_probe SET probe_value='updated' WHERE probe_id=?");update.setString(1,key);require(update.executeUpdate()==1,"Runtime UPDATE");
     var read=c.prepareStatement("SELECT probe_value FROM b_database_probe WHERE probe_id=?");read.setString(1,key);var rs=read.executeQuery();require(rs.next()&&"updated".equals(rs.getString(1)),"Runtime SELECT");
     var delete=c.prepareStatement("DELETE FROM b_database_probe WHERE probe_id=?");delete.setString(1,key);require(delete.executeUpdate()==1,"Runtime DELETE");
    }else{
     var insert=c.prepareStatement("INSERT INTO ab_trade_guard VALUES ('b06','web',?)");insert.setString(1,key);require(insert.executeUpdate()==1,"A INSERT");
     var read=c.prepareStatement("SELECT out_trade_no FROM ab_trade_guard WHERE source='b06' AND channel='web' AND out_trade_no=?");read.setString(1,key);var rs=read.executeQuery();require(rs.next()&&key.equals(rs.getString(1)),"A SELECT");
     var update=c.prepareStatement("UPDATE ab_trade_guard SET out_trade_no=out_trade_no WHERE source='b06' AND channel='web' AND out_trade_no=?");update.setString(1,key);update.executeUpdate();
     var delete=c.prepareStatement("DELETE FROM ab_trade_guard WHERE source='b06' AND channel='web' AND out_trade_no=?");delete.setString(1,key);require(delete.executeUpdate()==1,"A DELETE");
    }
   }finally{c.rollback();c.setAutoCommit(true);}
   denied(c,"DROP TABLE IF EXISTS b06_absent_probe");denied(c,"CREATE TABLE b06_forbidden (id INT)");denied(c,"ALTER TABLE `"+expected.iterator().next()+"` COMMENT='forbidden'");denied(c,"USE "+other);denied(c,"SELECT User FROM mysql.user LIMIT 0");
   denied(c,"GRANT SELECT ON "+schema+".* TO '"+who+"'@'%'");
   denied(c,"SELECT * FROM "+(who.equals("a_runtime")?"b06_init_journal":"flyway_schema_history")+" LIMIT 0");
  }
 }
 static void seed()throws Exception {
  var app=new SpringApplication(ZjMarketApplication.class);app.setWebApplicationType(WebApplicationType.NONE);
  try(var ctx=app.run("--spring.config.additional-location=file:/config/b.properties,file:/run/secrets/b.properties", "--b.identity.enabled=true","--b.product.enabled=true","--b.inventory.enabled=true","--b.infrastructure.rpc.enabled=false","--b.infrastructure.mq.enabled=false")){
   DataSource ds=ctx.getBean(DataSource.class);var jdbc=new JdbcTemplate(ds);var tx=new TransactionTemplate(new DataSourceTransactionManager(ds));
   String goods=tx.execute(status->{
    var identities=ctx.getBean(IIdentityService.class);var store=ctx.getBean(IIdentityRepository.class);var passwords=ctx.getBean(IPasswordPort.class);
    String opId=null;
    for(String name:List.of("b06operator","b06buyer","b06buyer2")){
     var u=store.userByLogin(name);String password=p.getProperty(name+".password");
     if(u==null){var v=name.equals("b06operator")?identities.initializeOperator(name,password,name):identities.register(name,password,name);u=store.userById(v.userId());}
     require(passwords.matches(password,u.passwordHash())&&u.enabled()&&u.roles().contains("USER")&&u.roles().contains("OPERATOR")==name.equals("b06operator"),"Seed account conflict");if(name.equals("b06operator"))opId=u.userId();
    }
    var previous=jdbc.queryForList("SELECT probe_value FROM b_database_probe WHERE probe_id='00000000-0000-0000-0000-000000000062'",String.class);
    if(!previous.isEmpty())return previous.getFirst();
    var product=ctx.getBean(IProductService.class).create(new ProductFields("B06 demonstration product","Windows Docker deployment sample",null,"100.00","CNY",SaleStatus.ON_SALE),"b06-initialization").product();
    ctx.getBean(IInventoryService.class).execute(opId,"b06-initial-stock",new InventoryRequest("INBOUND",product.goodsId(),100,1,"B06 initial stock"));
    jdbc.update("INSERT INTO b_database_probe VALUES ('00000000-0000-0000-0000-000000000062',?)",product.goodsId());return product.goodsId();
   });
   Files.writeString(Path.of("/output/seed-goods-id.txt"),goods+"\n");
  }
 }
 public static void main(String[] args)throws Exception {
  if(args[0].equals("selftest")){
   var parts=statements("CREATE TABLE t(c VARCHAR(9) COMMENT 'x;y'); SELECT 'a'';b'; SELECT `x;y`;");
   require(parts.size()==3 && parts.get(0).contains("'x;y'") && parts.get(1).contains("'a'';b'"),"Quoted statement splitter regression");
   boolean rejected=false;try{statements("SELECT 'unterminated;");}catch(IllegalStateException expected){rejected=true;}require(rejected,"Malformed literal must fail");System.out.println("DEPLOYMENT_PASS selftest");return;
  }
  try(var reader=Files.newBufferedReader(Path.of("/run/secrets/deployment.properties"))){p.load(reader);}
  try{switch(args[0]){case "a-init"->aInit();case "migrate"->migrate();case "verify"->verify();case "seed"->seed();default->throw new IllegalArgumentException();}System.out.println("DEPLOYMENT_PASS "+args[0]);}
  catch(Exception e){e.printStackTrace();System.err.println("DEPLOYMENT_FAILED "+args[0]+" "+e.getClass().getSimpleName());System.exit(1);}
 }
}
