package cn.bugstack.config;
import java.util.Collections;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
/** Internal process liveness only, not a claim of schema/business readiness. */
@RestController
public class LivenessController {
 @GetMapping("/internal/health/live")
 public Map<String,String> live(){return Collections.singletonMap("status","UP");}
}
