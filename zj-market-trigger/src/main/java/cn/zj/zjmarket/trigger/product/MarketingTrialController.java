package cn.zj.zjmarket.trigger.product;
import cn.zj.zjmarket.application.product.*;
import cn.zj.zjmarket.application.identity.*;
import cn.zj.zjmarket.trigger.identity.ApiResponse;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;
import org.springframework.boot.autoconfigure.condition.*;
import java.util.Map;
@RestController
@ConditionalOnWebApplication(type=ConditionalOnWebApplication.Type.SERVLET)
@ConditionalOnProperty(name="b.trial.enabled",havingValue="true")
public final class MarketingTrialController {
    private final MarketingTrialService service;
    public MarketingTrialController(MarketingTrialService service){this.service=service;}
    @PostMapping("/api/v1/products/{goodsId}/trial") ApiResponse trial(@PathVariable String goodsId,@RequestBody Map<String,Object> body,HttpServletRequest req){
        var principal=(IdentityService.Principal)req.getAttribute("b.principal");
        if(principal==null)throw new AuthFailure(401,"AUTH_REQUIRED");
        if(!principal.user().roles().contains("USER") && !principal.user().roles().contains("OPERATOR"))throw new AuthFailure(403,"FORBIDDEN");
        if(!body.isEmpty() || !req.getParameterMap().isEmpty())throw new ProductFailure(400,"VALIDATION_FAILED");
        String id=(String)req.getAttribute("b.requestId");return ApiResponse.ok(service.trial(principal.user().userId(),goodsId,id),id);
    }
}
