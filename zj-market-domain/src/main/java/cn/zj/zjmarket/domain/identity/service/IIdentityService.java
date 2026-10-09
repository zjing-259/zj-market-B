package cn.zj.zjmarket.domain.identity.service;

import cn.zj.zjmarket.domain.identity.model.valobj.AuthenticatedPrincipal;
import cn.zj.zjmarket.domain.identity.model.valobj.IdentityTokens;
import cn.zj.zjmarket.domain.identity.model.valobj.UserView;
public interface IIdentityService {
 UserView register(String loginName,String password,String displayName);
 UserView initializeOperator(String loginName,String password,String displayName);
 IdentityTokens login(String loginName,String password);
 IdentityTokens refresh(String raw);
 AuthenticatedPrincipal authenticate(String jwt);
 void logout(String access,String refresh);
}
