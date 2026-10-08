package cn.zj.zjmarket.trigger.identity;
import cn.zj.zjmarket.application.identity.*;
import jakarta.servlet.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
@RestController
@RequestMapping("/api/v1")
@org.springframework.boot.autoconfigure.condition.ConditionalOnWebApplication(type=org.springframework.boot.autoconfigure.condition.ConditionalOnWebApplication.Type.SERVLET)
@ConditionalOnProperty(name="b.identity.enabled",havingValue="true")
public final class IdentityController {
    private final IdentityService service;private final BrowserAuthPort browser;
    public IdentityController(IdentityService service,BrowserAuthPort browser){this.service=service;this.browser=browser;}
    public record Registration(String loginName,String password,String displayName) {}
    public record Login(String loginName,String password) {}
    public record TokenResponse(String accessToken,String tokenType,long expiresIn,Object user) {}
    @GetMapping("/auth/csrf") ApiResponse csrf(HttpServletRequest req,HttpServletResponse res){return ok(browser.csrf(res),req);}
    @PostMapping("/auth/register") ResponseEntity<ApiResponse> register(@RequestBody Registration body,HttpServletRequest req){
        browser.limit(req,body.loginName());
        if(body.displayName()==null) throw new AuthFailure(400,"VALIDATION_FAILED");
        return ResponseEntity.status(201).body(ok(service.register(body.loginName(),body.password(),body.displayName()),req));
    }
    @PostMapping("/auth/login") ApiResponse login(@RequestBody Login body,HttpServletRequest req,HttpServletResponse res){
        browser.limit(req,body.loginName());return tokenResponse(service.login(body.loginName(),body.password()),req,res);
    }
    @PostMapping("/auth/refresh") ApiResponse refresh(@RequestBody(required=false) java.util.Map<String,Object> body,HttpServletRequest req,HttpServletResponse res){
        empty(body);return tokenResponse(service.refresh(browser.refreshCookie(req)),req,res);
    }
    @PostMapping("/auth/logout") ApiResponse logout(@RequestBody(required=false) java.util.Map<String,Object> body,HttpServletRequest req,HttpServletResponse res){
        empty(body);service.logout(browser.bearer(req),browser.refreshCookie(req));browser.clear(res);return ok(null,req);
    }
    @GetMapping("/users/me") ApiResponse me(HttpServletRequest req){noQuery(req);return ok(principal(req).user(),req);}
    // A real operator-only identity endpoint; product routes are delivered in B-02.3.
    @GetMapping("/admin/users/me") ApiResponse operatorMe(HttpServletRequest req){if(!principal(req).user().roles().contains("OPERATOR"))throw new AuthFailure(403,"FORBIDDEN");noQuery(req);return ok(principal(req).user(),req);}
    private static IdentityService.Principal principal(HttpServletRequest req){
        var p=(IdentityService.Principal)req.getAttribute("b.principal");if(p==null)throw new AuthFailure(401,"AUTH_REQUIRED");return p;
    }
    private static void noQuery(HttpServletRequest req){if(!req.getParameterMap().isEmpty())throw new AuthFailure(400,"VALIDATION_FAILED");}
    private static void empty(java.util.Map<String,Object> body){if(body!=null && !body.isEmpty())throw new AuthFailure(400,"VALIDATION_FAILED");}
    private ApiResponse tokenResponse(IdentityService.Tokens tokens,HttpServletRequest req,HttpServletResponse res){
        browser.tokens(res,tokens);return ok(new TokenResponse(tokens.accessToken(),tokens.tokenType(),tokens.expiresIn(),tokens.user()),req);
    }
    private static ApiResponse ok(Object data,HttpServletRequest req){return ApiResponse.ok(data,(String)req.getAttribute("b.requestId"));}
}
