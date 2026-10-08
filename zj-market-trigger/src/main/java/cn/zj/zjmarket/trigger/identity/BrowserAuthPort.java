package cn.zj.zjmarket.trigger.identity;
import jakarta.servlet.http.*;
import cn.zj.zjmarket.application.identity.IdentityService;
public interface BrowserAuthPort {
    Object csrf(HttpServletResponse response);
    void tokens(HttpServletResponse response,IdentityService.Tokens tokens);
    void clear(HttpServletResponse response);
    String refreshCookie(HttpServletRequest request);
    String bearer(HttpServletRequest request);
    void limit(HttpServletRequest request,String loginName);
}
