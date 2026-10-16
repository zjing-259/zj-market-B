package cn.zj.zjmarket.app.security;

import cn.zj.zjmarket.domain.identity.service.IIdentityService;
import cn.zj.zjmarket.infrastructure.config.properties.IdentitySettings;
import cn.zj.zjmarket.types.exception.AuthFailure;
import jakarta.servlet.*;
import jakarta.servlet.http.*;
import java.io.IOException;
import java.util.UUID;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.web.servlet.HandlerMapping;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.dao.DataAccessException;
import org.springframework.transaction.TransactionException;
import org.springframework.web.filter.OncePerRequestFilter;
public final class IdentityHttpFilter extends OncePerRequestFilter {
    private final boolean requestLogging;
    private final IdentitySettings settings;private final ObjectProvider<IIdentityService> service;private final BrowserAuth browser;
    public IdentityHttpFilter(IdentitySettings settings,ObjectProvider<IIdentityService> service,BrowserAuth browser){this(settings,service,browser,false);}
    public IdentityHttpFilter(IdentitySettings settings,ObjectProvider<IIdentityService> service,BrowserAuth browser,boolean requestLogging){this.settings=settings;this.service=service;this.browser=browser;this.requestLogging=requestLogging;}
    protected void doFilterInternal(HttpServletRequest req,HttpServletResponse res,FilterChain chain)throws ServletException,IOException{
        String id=UUID.randomUUID().toString();req.setAttribute("b.requestId",id);res.setHeader("X-Request-Id",id);
        if(req.getRequestURI().startsWith("/api/"))res.setHeader("Cache-Control","no-store");
        long started=System.nanoTime();boolean completed=false;
        try(var ignored=MDC.putCloseable("requestId",id)){
          try{
            String path=req.getRequestURI();
            if(settings.isEnabled() && path.startsWith("/api/")){
                if(path.startsWith("/api/v1/auth/") && !req.getMethod().equals("GET"))browser.checkCsrf(req);
                if(!path.startsWith("/api/v1/auth/")){
                    String jwt=browser.bearer(req);
                    boolean protectedPath=path.startsWith("/api/v1/users/") || path.startsWith("/api/v1/admin/")
                        || (path.startsWith("/api/v1/products/") && (path.endsWith("/trial") || path.endsWith("/joinable-teams")));
                    if(jwt==null && protectedPath)throw new AuthFailure(401,"AUTH_REQUIRED");
                    if(jwt!=null){var principal=service.getObject().authenticate(jwt);req.setAttribute("b.principal",principal);
                        if(protectedPath && !principal.user().roles().contains("USER") && !principal.user().roles().contains("OPERATOR"))throw new AuthFailure(403,"FORBIDDEN");
                        if(path.startsWith("/api/v1/admin/") && !principal.user().roles().contains("OPERATOR"))throw new AuthFailure(403,"FORBIDDEN");}
                }
            }
            chain.doFilter(req,res);
        }catch(AuthFailure e){error(res,e.status(),e.code(),id);}
        catch(DataAccessException|TransactionException e){error(res,503,"DEPENDENCY_UNAVAILABLE",id);}
          completed=true;
        }finally{
            if(requestLogging && req.getRequestURI().startsWith("/api/")){
                Object pattern=req.getAttribute(HandlerMapping.BEST_MATCHING_PATTERN_ATTRIBUTE);
                String route=pattern instanceof String ? (String)pattern : "UNMAPPED";
                String method=java.util.Set.of("GET","POST","PUT","PATCH","DELETE","OPTIONS","HEAD").contains(req.getMethod())?req.getMethod():"OTHER";
                LoggerFactory.getLogger("b.observability.http").atInfo()
                    .addKeyValue("requestId",id).addKeyValue("route",route).addKeyValue("method",method)
                    .addKeyValue("status",completed?res.getStatus():500)
                    .addKeyValue("durationMs",(System.nanoTime()-started)/1_000_000)
                    .log("http_request_completed");
            }
        }
    }
    static void error(HttpServletResponse res,int status,String code,String id)throws IOException{
        res.setStatus(status);res.setContentType("application/json;charset=UTF-8");res.setHeader("Cache-Control","no-store");
        if(status==429)res.setHeader("Retry-After","60");
        if(status==401)res.setHeader("WWW-Authenticate","Bearer");
        res.getWriter().write("{\"code\":\""+code+"\",\"message\":\""+code+"\",\"data\":null,\"requestId\":\""+id+"\"}");
    }
}
