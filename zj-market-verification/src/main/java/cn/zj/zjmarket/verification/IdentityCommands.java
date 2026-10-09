package cn.zj.zjmarket.verification;

import cn.zj.zjmarket.ZjMarketApplication;
import cn.zj.zjmarket.domain.identity.adapter.port.IAccessTokenPort;
import cn.zj.zjmarket.domain.identity.adapter.port.IPasswordPort;
import cn.zj.zjmarket.domain.identity.adapter.repository.IIdentityRepository;
import cn.zj.zjmarket.domain.identity.model.entity.LoginGrant;
import cn.zj.zjmarket.domain.identity.model.entity.User;
import cn.zj.zjmarket.domain.identity.model.valobj.AccessTokenClaims;
import cn.zj.zjmarket.domain.identity.service.IIdentityService;
import cn.zj.zjmarket.domain.identity.service.impl.IdentityService;
import cn.zj.zjmarket.types.exception.AuthFailure;
import com.fasterxml.jackson.databind.*;
import java.net.*;
import java.net.http.*;
import java.nio.file.*;
import java.sql.*;
import java.util.*;
import java.util.concurrent.*;
import javax.sql.DataSource;
import org.springframework.boot.*;
import org.springframework.boot.web.server.context.WebServerApplicationContext;
/** Explicit identity acceptance and operator bootstrap, excluded from production JAR. */
public final class IdentityCommands {
    private static final ObjectMapper JSON=new ObjectMapper();
    private static final List<String> evidence=new ArrayList<>();
    public static int run(String mode){
        try {
            if(!Set.of("verify","init-operator").contains(mode))throw new IllegalArgumentException("Unsupported identity command");
            if(mode.equals("verify")) testGuard();
            SpringApplication app=new SpringApplication(ZjMarketApplication.class);
            if(mode.equals("init-operator"))app.setWebApplicationType(WebApplicationType.NONE);
            String[] args=mode.equals("verify")?new String[]{"--server.port=0","--b.identity.enabled=true","--b.product.enabled=false","--b.infrastructure.database.enabled=true","--b.trial.enabled=false","--b.sync.enabled=false","--b.infrastructure.rpc.enabled=false","--b.infrastructure.mq.enabled=false","--b.identity.rate.ip-limit=1000","--b.identity.rate.login-limit=20"}:
                new String[]{"--b.identity.enabled=true","--b.product.enabled=false","--b.infrastructure.database.enabled=true","--b.sync.enabled=false","--b.infrastructure.rpc.enabled=false","--b.infrastructure.mq.enabled=false"};
            try(var context=app.run(args)){
                var service=context.getBean(IIdentityService.class);
                if(mode.equals("init-operator")) {
                    var user=service.initializeOperator(required("B_OPERATOR_LOGIN_NAME"),required("B_OPERATOR_PASSWORD"),required("B_OPERATOR_DISPLAY_NAME"));
                    System.out.println("Operator initialized: "+user.userId());return 0;
                }
                int port=((WebServerApplicationContext)context).getWebServer().getPort();
                String base="http://127.0.0.1:"+port;
                String origin=required("B_IDENTITY_ORIGIN");
                var client=new Client(base,origin);
                String suffix=UUID.randomUUID().toString().replace("-","").substring(0,16);
                String login="u"+suffix, password="Test-"+UUID.randomUUID();
                var db=context.getBean(DataSource.class);
                evidence.add("java="+Runtime.version());evidence.add("springBoot="+SpringBootVersion.getVersion());
                var passwords=context.getBean(IPasswordPort.class);long start=System.nanoTime();
                String hash=passwords.encode(password);long encodeMs=(System.nanoTime()-start)/1000000;
                start=System.nanoTime();check(passwords.matches(password,hash),"argon2 match");long matchMs=(System.nanoTime()-start)/1000000;
                check(hash.startsWith("{argon2id}$argon2id$v=19$m=19456,t=2,p=1$"),"argon2 parameters");
                evidence.add("argon2id=19MiB,t2,p1;encodeMs="+encodeMs+";matchMs="+matchMs);
                String unicodePassword="🔑".repeat(64);IdentityService.validate("unicode",unicodePassword,null);
                String unicodeHash=passwords.encode(unicodePassword);check(passwords.matches(unicodePassword,unicodeHash),"64 Unicode code points, no bcrypt byte cap");
                evidence.add("password-64-Unicode-codepoints=PASSED");
                var registered=client.post("/auth/register",Map.of("loginName",login,"password",password,"displayName","测试用户"),null,201);
                String userId=registered.path("data").path("userId").asText();check(!userId.isBlank(),"userId");
                client.post("/auth/register",Map.of("loginName",login,"password",password,"displayName","duplicate"),null,409);
                client.post("/auth/register",Map.of("loginName","r"+suffix,"password",password,"displayName","rogue","roles",List.of("OPERATOR")),null,400);
                client.post("/auth/register",Map.of("loginName","UPPER","password",password,"displayName","bad"),null,400);
                client.post("/auth/register",Map.of("loginName","s"+suffix,"password","short","displayName","bad"),null,400);
                client.noCsrf("/auth/login",Map.of("loginName",login,"password",password),403);
                client.wrongOrigin("/auth/login",Map.of("loginName",login,"password",password),403);
                client.post("/auth/login",Map.of("loginName",login,"password",password+"wrong"),null,401);
                client.post("/auth/login",Map.of("loginName","absent"+suffix,"password",password),null,401);
                String jwt=client.login(login,password);String oldRefresh=client.refresh();
                var realTokensAtStart=context.getBean(IAccessTokenPort.class);
                var storeAtStart=context.getBean(IIdentityRepository.class);
                var grantBeforeRefresh=storeAtStart.grant(realTokensAtStart.verify(jwt).grantId());
                var me=client.get("/users/me",jwt,200);check(userId.equals(me.path("data").path("userId").asText()),"me identity");
                client.get("/users/me",null,401);client.get("/users/me?userId=spoof",jwt,400);client.get("/users/me",jwt.substring(0,jwt.length()-8)+"AAAAAAAA",401);
                client.get("/admin/users/me",jwt,403);client.get("/admin/products",jwt,403);client.post("/admin/products",Map.of("userId","spoof"),jwt,403);
                String fresh=client.post("/auth/refresh",Map.of(),null,200).path("data").path("accessToken").asText();
                check(!oldRefresh.equals(client.refresh()),"refresh rotates");
                check(grantBeforeRefresh.expiresAt()==storeAtStart.grant(realTokensAtStart.verify(fresh).grantId()).expiresAt(),"absolute refresh lifetime unchanged");client.setRefresh(oldRefresh);
                client.post("/auth/refresh",Map.of(),null,401);client.get("/users/me",fresh,401);
                evidence.add("register/validation/duplicate/escalation/CSRF/login/me/USER-denied=PASSED");
                evidence.add("refresh-rotation/absolute-lifetime/replay-family-revocation=PASSED");
                jwt=client.login(login,password);client.post("/auth/logout",Map.of(),jwt,200);client.get("/users/me",jwt,401);
                client.post("/auth/logout",Map.of(),null,200);
                jwt=client.login(login,password);
                try(var c=db.getConnection();var p=c.prepareStatement("UPDATE b_user SET enabled=FALSE,auth_version=auth_version+1 WHERE user_id=?")){p.setString(1,userId);p.executeUpdate();}
                client.get("/users/me",jwt,401);client.post("/auth/refresh",Map.of(),null,401);
                client.post("/auth/login",Map.of("loginName",login,"password",password),null,401);
                try(var c=db.getConnection();var p=c.prepareStatement("UPDATE b_user SET enabled=TRUE WHERE user_id=?")){p.setString(1,userId);p.executeUpdate();}
                String operator="o"+suffix;var operatorUser=service.initializeOperator(operator,password,"test operator");
                var op=new Client(base,origin);String opJwt=op.login(operator,password);op.get("/admin/users/me",opJwt,200);
                try(var c=db.getConnection();var p=c.prepareStatement("DELETE FROM b_user_role WHERE user_id=? AND role='OPERATOR'")){p.setString(1,operatorUser.userId());p.executeUpdate();}
                op.get("/admin/users/me",opJwt,403);op.get("/users/me",opJwt,200);
                try(var c=db.getConnection();var p=c.prepareStatement("INSERT INTO b_user_role(user_id,role) VALUES(?,'OPERATOR')")){p.setString(1,operatorUser.userId());p.executeUpdate();}
                try(var c=db.getConnection();var p=c.prepareStatement("DELETE FROM b_user_role WHERE user_id=?")){p.setString(1,operatorUser.userId());p.executeUpdate();}
                op.get("/users/me",opJwt,403);
                try(var c=db.getConnection();var p=c.prepareStatement("INSERT INTO b_user_role(user_id,role) VALUES(?,'USER'),(?,'OPERATOR')")){p.setString(1,operatorUser.userId());p.setString(2,operatorUser.userId());p.executeUpdate();}
                evidence.add("logout-idempotency/JWT-revocation/user-disabled/current-roles/roleless-denied/OPERATOR-allowed=PASSED");
                // Explicit transaction rollback must leave no partial account/role.
                var store=context.getBean(IIdentityRepository.class);
                try{store.transaction(() -> {store.insertUser(new User(UUID.randomUUID().toString(),"rollback"+suffix,"rollback",hash,true,1,Set.of("USER")));throw new IllegalStateException("intentional rollback");});}
                catch(IllegalStateException expected){}
                check(store.userByLogin("rollback"+suffix)==null,"transaction rollback");
                // Issuer failure after grant/token writes must roll back both tables.
                long before=countGrants(db,userId);
                var realTokens=context.getBean(IAccessTokenPort.class);
                var failingTokens=new IAccessTokenPort(){
                    public String issue(User user,cn.zj.zjmarket.domain.identity.model.entity.LoginGrant grant,long now,long expiry){throw new AuthFailure(503,"DEPENDENCY_UNAVAILABLE");}
                    public AccessTokenClaims verify(String token){return realTokens.verify(token);}
                };
                var failedIssuer=new IdentityService(store,passwords,failingTokens,java.time.Clock.systemUTC(),900,604800);
                try{failedIssuer.login(login,password);throw new IllegalStateException("check: issuer failure expected");}
                catch(AuthFailure expected){check(expected.status()==503,"issuer failure");}
                check(before==countGrants(db,userId),"failed signing grant rollback");
                // Real expired RS256 JWT, then logout fallback using the valid cookie.
                var expiry=new Client(base,origin);String active=expiry.login(login,password);
                var claims=realTokens.verify(active);long time=java.time.Instant.now().getEpochSecond();
                String expired=realTokens.issue(store.userById(userId),store.grant(claims.grantId()),time-901,time-1);
                expiry.get("/users/me",expired,401);expiry.post("/auth/logout",Map.of(),expired,200);expiry.get("/users/me",active,401);
                evidence.add("MyBatis-mapper/transaction-rollback/signing-failure-rollback/expired-JWT/logout-cookie-fallback=PASSED");
                // Two HTTP refreshes with the same old credential: one rotates, the other revokes.
                var race=new Client(base,origin);race.login(login,password);String raw=race.refresh();
                var first=new Client(base,origin);var second=new Client(base,origin);first.setRefresh(raw);second.setRefresh(raw);
                try(var executor=Executors.newVirtualThreadPerTaskExecutor()){
                    var a=executor.submit(() -> first.postAny("/auth/refresh",Map.of()));
                    var b=executor.submit(() -> second.postAny("/auth/refresh",Map.of()));
                    var ra=a.get();var rb=b.get();check(Set.of(ra.statusCode(),rb.statusCode()).equals(Set.of(200,401)),"concurrent refresh status");
                    String issued=JSON.readTree((ra.statusCode()==200?ra:rb).body()).path("data").path("accessToken").asText();race.get("/users/me",issued,401);
                }
                evidence.add("concurrent-refresh-one-success/replay-revocation-committed=PASSED");
                var deadlineClient=new Client(base,origin);String deadlineJwt=deadlineClient.login(login,password);
                var futureClock=java.time.Clock.fixed(java.time.Instant.now().plusSeconds(604801),java.time.ZoneOffset.UTC);
                var futureService=new IdentityService(store,passwords,realTokens,futureClock,900,604800);
                try{futureService.refresh(deadlineClient.refresh());throw new IllegalStateException("check: expired refresh expected");}
                catch(AuthFailure expected){check(expected.status()==401,"refresh absolute expiry");}
                deadlineClient.get("/users/me",deadlineJwt,401);
                evidence.add("refresh-absolute-expiry=PASSED (controlled application clock, actual test DB)");
                var rate=new Client(base,origin);for(int i=0;i<20;i++)rate.post("/auth/login",Map.of("loginName","limited"+suffix,"password",password),null,401);
                var limited=rate.postAny("/auth/login",Map.of("loginName","limited"+suffix,"password",password));check(limited.statusCode()==429 && limited.headers().firstValue("Retry-After").isPresent(),"rate limit");
                // Kill the B test datasource only, leave MySQL and all other schemas untouched.
                ((com.zaxxer.hikari.HikariDataSource)db).close();op.get("/users/me",opJwt,503);
                evidence.add("rate-limit/Retry-After/auth-database-unavailable-fail-closed=PASSED");
                evidence.add("status=PASSED");
                Path report=Path.of(required("B_IDENTITY_REPORT"));Files.createDirectories(report.toAbsolutePath().getParent());Files.write(report,evidence);
                System.out.println("B identity actual HTTP verification: PASSED");
            }
            return 0;
        }catch(Exception e){System.err.println("B identity command failed: "+e.getClass().getSimpleName()+" "+safeReason(e));return 1;}
    }
    private static long countGrants(DataSource source,String userId)throws SQLException{
        try(var c=source.getConnection();var p=c.prepareStatement("SELECT COUNT(*) FROM b_login_grant WHERE user_id=?")){p.setString(1,userId);try(var rows=p.executeQuery()){rows.next();return rows.getLong(1);}}
    }
    private static String safeReason(Exception e){return (e instanceof IllegalStateException && e.getMessage()!=null && e.getMessage().startsWith("check:"))?e.getMessage():"details withheld";}
    private static void testGuard(){
        if(!"b02-test".equals(required("B_DATABASE_SCOPE")) || !required("B_DATABASE_URL").matches("^jdbc:mysql://[^/]+/zj_market_b02_test(?:\\?.*)?$")
            || !"zj_market_b02_test_app".equals(required("B_DATABASE_USERNAME")))throw new IllegalArgumentException("Identity acceptance requires exact isolated B test schema/account");
    }
    private static String required(String key){String value=System.getenv(key);if(value==null || value.isBlank())throw new IllegalArgumentException("Missing "+key);return value;}
    private static void check(boolean value,String name){if(!value)throw new IllegalStateException("check: "+name);}
    private static final class Client {
        final String base,origin;final CookieManager cookies=new CookieManager(null,CookiePolicy.ACCEPT_ALL);
        final HttpClient http=HttpClient.newBuilder().cookieHandler(cookies).connectTimeout(java.time.Duration.ofSeconds(5)).build();
        Client(String base,String origin){this.base=base;this.origin=origin;}
        JsonNode get(String path,String token,int expected)throws Exception{return response(send("GET",path,null,token,null,null),expected);}
        JsonNode post(String path,Object body,String jwt,int expected)throws Exception{return response(sendPost(path,body,jwt,origin,true),expected);}
        HttpResponse<String> postAny(String path,Object body)throws Exception{return sendPost(path,body,null,origin,true);}
        void noCsrf(String path,Object body,int expected)throws Exception{response(sendPost(path,body,null,origin,false),expected);}
        void wrongOrigin(String path,Object body,int expected)throws Exception{response(sendPost(path,body,null,"https://evil.example",true),expected);}
        HttpResponse<String> sendPost(String path,Object body,String jwt,String source,boolean csrf)throws Exception{
            String token=csrf?get("/auth/csrf",null,200).path("data").path("token").asText():null;
            return send("POST",path,body,jwt,source,token);
        }
        HttpResponse<String> send(String method,String path,Object body,String jwt,String source,String csrf)throws Exception{
            var builder=HttpRequest.newBuilder(URI.create(base+"/api/v1"+path)).timeout(java.time.Duration.ofSeconds(20));
            if(jwt!=null)builder.header("Authorization","Bearer "+jwt);if(source!=null)builder.header("Origin",source);if(csrf!=null)builder.header("X-CSRF-TOKEN",csrf);
            if(body!=null)builder.header("Content-Type","application/json");
            builder.method(method,body==null?HttpRequest.BodyPublishers.noBody():HttpRequest.BodyPublishers.ofString(JSON.writeValueAsString(body)));
            return http.send(builder.build(),HttpResponse.BodyHandlers.ofString());
        }
        JsonNode response(HttpResponse<String> result,int expected)throws Exception{
            check(result.statusCode()==expected,"HTTP "+result.request().uri().getPath()+" status "+result.statusCode()+" expected "+expected);
            var json=JSON.readTree(result.body());check(result.headers().firstValue("X-Request-Id").orElse("").equals(json.path("requestId").asText()),"requestId envelope");
            check(result.headers().firstValue("Cache-Control").orElse("").contains("no-store"),"no-store");return json;
        }
        String login(String login,String password)throws Exception{return post("/auth/login",Map.of("loginName",login,"password",password),null,200).path("data").path("accessToken").asText();}
        String refresh(){return cookies.getCookieStore().getCookies().stream().filter(c -> c.getName().equals("B_REFRESH")).findFirst().orElseThrow().getValue();}
        void setRefresh(String value){var uri=URI.create(base);for(var c:new ArrayList<>(cookies.getCookieStore().getCookies()))if(c.getName().equals("B_REFRESH"))cookies.getCookieStore().remove(uri,c);
            var cookie=new HttpCookie("B_REFRESH",value);cookie.setPath("/api/v1/auth");cookie.setDomain(uri.getHost());cookie.setVersion(0);cookies.getCookieStore().add(uri,cookie);}
    }
}
