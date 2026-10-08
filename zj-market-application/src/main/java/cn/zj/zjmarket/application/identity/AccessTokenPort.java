package cn.zj.zjmarket.application.identity;
import cn.zj.zjmarket.domain.identity.*;
public interface AccessTokenPort {
    String issue(User user, LoginGrant grant, long now, long expiresAt);
    Claims verify(String token);
    record Claims(String userId, String grantId, long authVersion) {}
}
