package cn.zj.zjmarket.domain.identity.model.entity;

import cn.zj.zjmarket.domain.identity.model.valobj.UserView;
import java.util.Set;
public record User(String userId, String loginName, String displayName, String passwordHash,
                   boolean enabled, long authVersion, Set<String> roles) {
    public User { roles = Set.copyOf(roles); }
    public UserView view() { return new UserView(userId, loginName, displayName, roles); }


}
