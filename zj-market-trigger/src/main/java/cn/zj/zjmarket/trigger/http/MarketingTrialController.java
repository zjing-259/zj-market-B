package cn.zj.zjmarket.trigger.http;

import cn.zj.zjmarket.api.response.ApiResponse;
import cn.zj.zjmarket.domain.identity.model.valobj.AuthenticatedPrincipal;
import cn.zj.zjmarket.domain.product.service.IMarketingTrialService;
import cn.zj.zjmarket.types.exception.AuthFailure;
import cn.zj.zjmarket.types.exception.ProductFailure;
import jakarta.servlet.http.HttpServletRequest;
import java.util.Map;
import org.springframework.boot.autoconfigure.condition.*;
import org.springframework.web.bind.annotation.*;
@RestController
@ConditionalOnWebApplication(type=ConditionalOnWebApplication.Type.SERVLET)
@ConditionalOnProperty(name="b.trial.enabled",havingValue="true")
public final class MarketingTrialController {
    private final IMarketingTrialService service;
    public MarketingTrialController(IMarketingTrialService service){this.service=service;}
    @PostMapping("/api/v1/products/{goodsId}/trial") ApiResponse trial(@PathVariable String goodsId,@RequestBody Map<String,Object> body,HttpServletRequest req){
        var principal=(AuthenticatedPrincipal)req.getAttribute("b.principal");
        if(principal==null)throw new AuthFailure(401,"AUTH_REQUIRED");
        if(!principal.user().roles().contains("USER") && !principal.user().roles().contains("OPERATOR"))throw new AuthFailure(403,"FORBIDDEN");
        if(!body.isEmpty() || !req.getParameterMap().isEmpty())throw new ProductFailure(400,"VALIDATION_FAILED");
        String id=(String)req.getAttribute("b.requestId");return ApiResponse.ok(service.trial(principal.user().userId(),goodsId,id),id);
    }
}
