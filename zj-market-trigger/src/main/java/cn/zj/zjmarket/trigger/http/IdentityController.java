package cn.zj.zjmarket.trigger.http;

import cn.zj.zjmarket.api.dto.identity.LoginRequestDTO;
import cn.zj.zjmarket.api.dto.identity.RegistrationRequestDTO;
import cn.zj.zjmarket.api.dto.identity.TokenResponseDTO;
import cn.zj.zjmarket.api.response.ApiResponse;
import cn.zj.zjmarket.domain.identity.model.valobj.AuthenticatedPrincipal;
import cn.zj.zjmarket.domain.identity.model.valobj.IdentityTokens;
import cn.zj.zjmarket.domain.identity.service.IIdentityService;
import cn.zj.zjmarket.trigger.adapter.port.IBrowserAuthPort;
import cn.zj.zjmarket.types.exception.AuthFailure;
import jakarta.servlet.http.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
@RestController
@RequestMapping("/api/v1")
@org.springframework.boot.autoconfigure.condition.ConditionalOnWebApplication(type=org.springframework.boot.autoconfigure.condition.ConditionalOnWebApplication.Type.SERVLET)
@ConditionalOnProperty(name="b.identity.enabled",havingValue="true")
public final class IdentityController {
    private final IIdentityService service;private final IBrowserAuthPort browser;
    public IdentityController(IIdentityService service,IBrowserAuthPort browser){this.service=service;this.browser=browser;}


    @GetMapping("/auth/csrf") ApiResponse csrf(HttpServletRequest req,HttpServletResponse res){return ok(browser.csrf(res),req);}
    @PostMapping("/auth/register") ResponseEntity<ApiResponse> register(@RequestBody RegistrationRequestDTO body,HttpServletRequest req){
        browser.limit(req,body.loginName());
        if(body.displayName()==null) throw new AuthFailure(400,"VALIDATION_FAILED");
        return ResponseEntity.status(201).body(ok(service.register(body.loginName(),body.password(),body.displayName()),req));
    }
    @PostMapping("/auth/login") ApiResponse login(@RequestBody LoginRequestDTO body,HttpServletRequest req,HttpServletResponse res){
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
    private static AuthenticatedPrincipal principal(HttpServletRequest req){
        var p=(AuthenticatedPrincipal)req.getAttribute("b.principal");if(p==null)throw new AuthFailure(401,"AUTH_REQUIRED");return p;
    }
    private static void noQuery(HttpServletRequest req){if(!req.getParameterMap().isEmpty())throw new AuthFailure(400,"VALIDATION_FAILED");}
    private static void empty(java.util.Map<String,Object> body){if(body!=null && !body.isEmpty())throw new AuthFailure(400,"VALIDATION_FAILED");}
    private ApiResponse tokenResponse(IdentityTokens tokens,HttpServletRequest req,HttpServletResponse res){
        browser.tokens(res,tokens);return ok(new TokenResponseDTO(tokens.accessToken(),tokens.tokenType(),tokens.expiresIn(),tokens.user()),req);
    }
    private static ApiResponse ok(Object data,HttpServletRequest req){return ApiResponse.ok(data,(String)req.getAttribute("b.requestId"));}
}
