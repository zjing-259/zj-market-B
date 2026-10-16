package cn.zj.zjmarket.trigger.http;
import cn.zj.zjmarket.api.response.ApiResponse;
import cn.zj.zjmarket.domain.identity.model.valobj.AuthenticatedPrincipal;
import cn.zj.zjmarket.domain.order.service.ITeamDiscoveryService;
import cn.zj.zjmarket.types.exception.AuthFailure;
import cn.zj.zjmarket.types.exception.ProductFailure;
import jakarta.servlet.http.HttpServletRequest;
import java.util.*;
import org.springframework.boot.autoconfigure.condition.*;
import org.springframework.web.bind.annotation.*;
@RestController
@ConditionalOnWebApplication(type=ConditionalOnWebApplication.Type.SERVLET)
@ConditionalOnProperty(name="b.team-discovery.enabled",havingValue="true")
public final class TeamDiscoveryController {
 private final ITeamDiscoveryService service;private final TeamDiscoveryGate gate;
 public TeamDiscoveryController(ITeamDiscoveryService service,TeamDiscoveryGate gate){this.service=service;this.gate=gate;}
 @GetMapping("/api/v1/products/{goodsId}/joinable-teams") ApiResponse list(@PathVariable String goodsId,HttpServletRequest req){
  var principal=(AuthenticatedPrincipal)req.getAttribute("b.principal");if(principal==null)throw new AuthFailure(401,"AUTH_REQUIRED");
  if(!principal.user().roles().contains("USER")&&!principal.user().roles().contains("OPERATOR"))throw new AuthFailure(403,"FORBIDDEN");
  if(req.getContentLengthLong()>0||req.getHeader("Transfer-Encoding")!=null)throw invalid();
  if(req.getParameterMap().entrySet().stream().anyMatch(e->!Set.of("limit","cursor").contains(e.getKey())||e.getValue().length!=1))throw invalid();
  String raw=req.getParameter("limit");int limit=3;if(raw!=null){if(!raw.matches("[1-9][0-9]?")||Integer.parseInt(raw)>10)throw invalid();limit=Integer.parseInt(raw);}
  String cursor=req.getParameter("cursor");if(cursor!=null&&(cursor.isEmpty()||cursor.length()>1024||!cursor.matches("[A-Za-z0-9_-]+")))throw invalid();
  if(goodsId==null||!goodsId.matches("[A-Za-z0-9._-]{1,64}"))throw invalid();
  String user=principal.user().userId(),id=(String)req.getAttribute("b.requestId");int size=limit;
  long started=System.nanoTime();var page=gate.run(user,()->service.list(user,goodsId,size,cursor,id));
  System.getLogger("b.team.discovery").log(System.Logger.Level.INFO,"discovery_read_completed requestId="+id+" goodsId="+goodsId+" activityId="+(page.activityId()==null?"-":page.activityId())+" state="+page.state()+" itemCount="+page.items().size()+" durationMs="+(System.nanoTime()-started)/1_000_000);
  return ApiResponse.ok(page,id);
 }
 private static ProductFailure invalid(){return new ProductFailure(400,"VALIDATION_FAILED");}
}
