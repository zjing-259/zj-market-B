package cn.zj.zjmarket.web;
import cn.zj.zjmarket.trigger.identity.BrowserAuthPort;
import cn.zj.zjmarket.application.identity.*;
import cn.zj.zjmarket.infrastructure.identity.IdentitySettings;
import jakarta.servlet.http.*;
import org.springframework.http.ResponseCookie;
import java.security.*;
import java.util.*;
public final class BrowserAuth implements BrowserAuthPort {
    private final IdentitySettings settings;private final LoginRateLimiter limiter;
    private final SecureRandom random=new SecureRandom();
    public BrowserAuth(IdentitySettings settings,LoginRateLimiter limiter){this.settings=settings;this.limiter=limiter;}
    private void cookie(HttpServletResponse response,String name,String value,long age){
        response.addHeader("Set-Cookie",ResponseCookie.from(name,value).path("/api/v1/auth").httpOnly(true)
            .secure(settings.isSecureCookies()).sameSite("Lax").maxAge(age).build().toString());
    }
    public Object csrf(HttpServletResponse response){
        byte[] bytes=new byte[32];random.nextBytes(bytes);String token=Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
        cookie(response,"B_CSRF",token,settings.getRefreshSeconds());response.setHeader("Cache-Control","no-store");
        return Map.of("token",token,"headerName","X-CSRF-TOKEN");
    }
    public void tokens(HttpServletResponse response,IdentityService.Tokens tokens){cookie(response,"B_REFRESH",tokens.refreshToken(),tokens.refreshExpiresIn());csrf(response);}
    public void clear(HttpServletResponse response){cookie(response,"B_REFRESH","",0);csrf(response);}
    public String refreshCookie(HttpServletRequest req){return cookie(req,"B_REFRESH");}
    public static String cookie(HttpServletRequest req,String name){
        String result=null;if(req.getCookies()!=null)for(var cookie:req.getCookies())if(cookie.getName().equals(name)) {
            if(result!=null)throw new AuthFailure(403,"CSRF_INVALID");result=cookie.getValue();
        }return result;
    }
    public String bearer(HttpServletRequest req){
        String header=req.getHeader("Authorization");if(header==null)return null;
        if(!header.startsWith("Bearer ") || header.length()<8)throw new AuthFailure(401,"TOKEN_INVALID");return header.substring(7);
    }
    public void limit(HttpServletRequest request,String name){limiter.check(request.getRemoteAddr(),name);}
    public void checkCsrf(HttpServletRequest req){
        String origin=req.getHeader("Origin");
        if(origin==null){String referer=req.getHeader("Referer");try{if(referer!=null){var uri=java.net.URI.create(referer);origin=uri.getScheme()+"://"+uri.getRawAuthority();}}catch(IllegalArgumentException ignored){}}
        String header=req.getHeader("X-CSRF-TOKEN"), cookie=cookie(req,"B_CSRF");
        if(!settings.getOrigin().equals(origin) || header==null || cookie==null || !cookie.matches("[A-Za-z0-9_-]{43}")
            || !MessageDigest.isEqual(header.getBytes(java.nio.charset.StandardCharsets.UTF_8),cookie.getBytes(java.nio.charset.StandardCharsets.UTF_8)))
            throw new AuthFailure(403,"CSRF_INVALID");
    }
}
