package cn.zj.zjmarket.trigger.http;
import cn.zj.zjmarket.api.response.ApiResponse;
import cn.zj.zjmarket.domain.identity.model.valobj.AuthenticatedPrincipal;
import cn.zj.zjmarket.domain.order.service.ITeamService;
import cn.zj.zjmarket.types.exception.AuthFailure;
import cn.zj.zjmarket.domain.order.model.valobj.PurchaseConditions;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.boot.autoconfigure.condition.*;
import org.springframework.web.bind.annotation.*;
@RestController @ConditionalOnWebApplication(type=ConditionalOnWebApplication.Type.SERVLET)
@ConditionalOnProperty(name="b.trade.enabled",havingValue="true")
public final class TeamController {
 private final ITeamService service;public TeamController(ITeamService service){this.service=service;}
 @GetMapping("/api/v1/teams/{teamId}") ApiResponse team(@PathVariable String teamId,HttpServletRequest r){var p=(AuthenticatedPrincipal)r.getAttribute("b.principal");if(p==null)throw new AuthFailure(401,"AUTH_REQUIRED");if(!p.user().roles().contains("USER")&&!p.user().roles().contains("OPERATOR"))throw new AuthFailure(403,"FORBIDDEN");if(!r.getParameterMap().isEmpty())throw PurchaseConditions.invalid();String id=(String)r.getAttribute("b.requestId");return ApiResponse.ok(service.query(p.user().userId(),teamId,id),id);}
}
