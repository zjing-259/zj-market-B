package cn.zj.zjmarket.web;
import cn.zj.zjmarket.application.identity.IdentityService;
import cn.zj.zjmarket.infrastructure.identity.IdentitySettings;
import cn.zj.zjmarket.trigger.identity.BrowserAuthPort;
import org.springframework.context.annotation.*;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.AnonymousAuthenticationFilter;
import org.springframework.security.core.userdetails.*;
@Configuration(proxyBeanMethods=false)
@Import(IdentityErrors.class)
@org.springframework.boot.autoconfigure.condition.ConditionalOnWebApplication(type=org.springframework.boot.autoconfigure.condition.ConditionalOnWebApplication.Type.SERVLET)
public class IdentityWebConfiguration {
    @Bean UserDetailsService noDefaultUsers(){return name -> {throw new UsernameNotFoundException("No implicit users");};}
    @Bean BrowserAuthPort browserAuth(IdentitySettings settings,
       @Value("${b.identity.rate.ip-limit:20}")int ip,@Value("${b.identity.rate.login-limit:5}")int login,
       @Value("${b.identity.rate.window-seconds:60}")long seconds){return new BrowserAuth(settings,new LoginRateLimiter(ip,login,seconds));}
    @Bean SecurityFilterChain apiSecurity(HttpSecurity http,IdentitySettings settings,ObjectProvider<IdentityService> service,BrowserAuthPort browser)throws Exception {
        http.csrf(csrf -> csrf.disable()).cors(cors -> cors.disable()).formLogin(login -> login.disable()).httpBasic(basic -> basic.disable())
            .logout(logout -> logout.disable()).requestCache(cache -> cache.disable())
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth.anyRequest().permitAll())
            .addFilterBefore(new IdentityHttpFilter(settings,service,(BrowserAuth)browser),AnonymousAuthenticationFilter.class);
        return http.build();
    }
}
