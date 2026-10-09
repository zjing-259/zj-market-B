package cn.zj.zjmarket.trigger.adapter.port;

import cn.zj.zjmarket.domain.identity.model.valobj.IdentityTokens;
import jakarta.servlet.http.*;
public interface IBrowserAuthPort {
    Object csrf(HttpServletResponse response);
    void tokens(HttpServletResponse response,IdentityTokens tokens);
    void clear(HttpServletResponse response);
    String refreshCookie(HttpServletRequest request);
    String bearer(HttpServletRequest request);
    void limit(HttpServletRequest request,String loginName);
}
