package cn.zj.zjmarket.app.config;

import cn.zj.zjmarket.app.security.BrowserAuth;
import cn.zj.zjmarket.app.security.IdentityErrors;
import cn.zj.zjmarket.app.security.IdentityHttpFilter;
import cn.zj.zjmarket.app.security.LoginRateLimiter;
import cn.zj.zjmarket.domain.identity.service.IIdentityService;
import cn.zj.zjmarket.infrastructure.config.properties.IdentitySettings;
import cn.zj.zjmarket.trigger.adapter.port.IBrowserAuthPort;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.*;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.*;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.AnonymousAuthenticationFilter;
@Configuration(proxyBeanMethods=false)
@Import(cn.zj.zjmarket.app.security.IdentityErrors.class)
@org.springframework.boot.autoconfigure.condition.ConditionalOnWebApplication(type=org.springframework.boot.autoconfigure.condition.ConditionalOnWebApplication.Type.SERVLET)
public class IdentityWebConfiguration {
    @Bean org.springframework.boot.jackson.autoconfigure.JsonFactoryBuilderCustomizer rejectDuplicateJsonFields(){return builder -> builder.enable(tools.jackson.core.StreamReadFeature.STRICT_DUPLICATE_DETECTION);}
    @Bean UserDetailsService noDefaultUsers(){return name -> {throw new UsernameNotFoundException("No implicit users");};}
    @Bean IBrowserAuthPort browserAuth(IdentitySettings settings,
       @Value("${b.identity.rate.ip-limit:20}")int ip,@Value("${b.identity.rate.login-limit:5}")int login,
       @Value("${b.identity.rate.window-seconds:60}")long seconds){return new BrowserAuth(settings,new LoginRateLimiter(ip,login,seconds));}
    @Bean SecurityFilterChain apiSecurity(HttpSecurity http,IdentitySettings settings,ObjectProvider<IIdentityService> service,IBrowserAuthPort browser,@org.springframework.beans.factory.annotation.Value("${b.observability.request-logging-enabled:false}") boolean requestLogging)throws Exception {
        http.csrf(csrf -> csrf.disable()).cors(cors -> cors.disable()).formLogin(login -> login.disable()).httpBasic(basic -> basic.disable())
            .logout(logout -> logout.disable()).requestCache(cache -> cache.disable())
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth.anyRequest().permitAll())
            .addFilterBefore(new IdentityHttpFilter(settings,service,(BrowserAuth)browser,requestLogging),AnonymousAuthenticationFilter.class);
        return http.build();
    }
}
