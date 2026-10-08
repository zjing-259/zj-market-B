package cn.zj.zjmarket.web;
import cn.zj.zjmarket.application.identity.*;
import cn.zj.zjmarket.infrastructure.identity.IdentitySettings;
import cn.zj.zjmarket.trigger.identity.ApiResponse;
import jakarta.servlet.*;
import jakarta.servlet.http.*;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.dao.DataAccessException;
import org.springframework.transaction.TransactionException;
import java.io.IOException;
import java.util.UUID;
public final class IdentityHttpFilter extends OncePerRequestFilter {
    private final IdentitySettings settings;private final ObjectProvider<IdentityService> service;private final BrowserAuth browser;
    public IdentityHttpFilter(IdentitySettings settings,ObjectProvider<IdentityService> service,BrowserAuth browser){this.settings=settings;this.service=service;this.browser=browser;}
    protected void doFilterInternal(HttpServletRequest req,HttpServletResponse res,FilterChain chain)throws ServletException,IOException{
        String id=UUID.randomUUID().toString();req.setAttribute("b.requestId",id);res.setHeader("X-Request-Id",id);
        if(req.getRequestURI().startsWith("/api/"))res.setHeader("Cache-Control","no-store");
        try{
            String path=req.getRequestURI();
            if(settings.isEnabled() && path.startsWith("/api/")){
                if(path.startsWith("/api/v1/auth/") && !req.getMethod().equals("GET"))browser.checkCsrf(req);
                if(!path.startsWith("/api/v1/auth/")){
                    String jwt=browser.bearer(req);
                    boolean protectedPath=path.startsWith("/api/v1/users/") || path.startsWith("/api/v1/admin/")
                        || (path.startsWith("/api/v1/products/") && path.endsWith("/trial"));
                    if(jwt==null && protectedPath)throw new AuthFailure(401,"AUTH_REQUIRED");
                    if(jwt!=null){var principal=service.getObject().authenticate(jwt);req.setAttribute("b.principal",principal);
                        if(protectedPath && !principal.user().roles().contains("USER") && !principal.user().roles().contains("OPERATOR"))throw new AuthFailure(403,"FORBIDDEN");
                        if(path.startsWith("/api/v1/admin/") && !principal.user().roles().contains("OPERATOR"))throw new AuthFailure(403,"FORBIDDEN");}
                }
            }
            chain.doFilter(req,res);
        }catch(AuthFailure e){error(res,e.status(),e.code(),id);}
        catch(DataAccessException|TransactionException e){error(res,503,"DEPENDENCY_UNAVAILABLE",id);}
    }
    static void error(HttpServletResponse res,int status,String code,String id)throws IOException{
        res.setStatus(status);res.setContentType("application/json;charset=UTF-8");res.setHeader("Cache-Control","no-store");
        if(status==429)res.setHeader("Retry-After","60");
        if(status==401)res.setHeader("WWW-Authenticate","Bearer");
        res.getWriter().write("{\"code\":\""+code+"\",\"message\":\""+code+"\",\"data\":null,\"requestId\":\""+id+"\"}");
    }
}
