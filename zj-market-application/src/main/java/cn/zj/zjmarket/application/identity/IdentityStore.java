package cn.zj.zjmarket.application.identity;
import cn.zj.zjmarket.domain.identity.*;
import java.util.function.Supplier;
public interface IdentityStore {
    <T> T transaction(Supplier<T> work);
    User userByLogin(String loginName);
    User userById(String userId);
    User lockUser(String userId);
    void insertUser(User user);
    LoginGrant grant(String grantId);
    LoginGrant lockGrant(String grantId);
    void insertGrant(LoginGrant grant);
    void revoke(String grantId);
    RefreshCredential refresh(String digest);
    void insertRefresh(RefreshCredential token);
    void useRefresh(String digest);
}
