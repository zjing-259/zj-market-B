package cn.zj.zjmarket.domain.identity.adapter.port;

import cn.zj.zjmarket.domain.identity.model.entity.LoginGrant;
import cn.zj.zjmarket.domain.identity.model.entity.User;
import cn.zj.zjmarket.domain.identity.model.valobj.AccessTokenClaims;
public interface IAccessTokenPort {
    String issue(User user, LoginGrant grant, long now, long expiresAt);
    AccessTokenClaims verify(String token);


}
