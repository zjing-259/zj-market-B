package cn.zj.zjmarket.domain.identity;
import java.util.Set;
public record User(String userId, String loginName, String displayName, String passwordHash,
                   boolean enabled, long authVersion, Set<String> roles) {
    public User { roles = Set.copyOf(roles); }
    public View view() { return new View(userId, loginName, displayName, roles); }
    public record View(String userId, String loginName, String displayName, Set<String> roles) {}
}
