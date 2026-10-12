package cn.zj.zjmarket.app.health;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
/** Internal process liveness. Dependency/schema readiness is checked separately at deployment. */
@RestController
public final class LivenessController {
    @GetMapping("/internal/health/live")
    public Map<String, String> live() { return Map.of("status", "UP"); }
}
