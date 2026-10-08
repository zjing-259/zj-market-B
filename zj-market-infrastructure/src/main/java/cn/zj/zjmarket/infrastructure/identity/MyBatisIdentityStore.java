package cn.zj.zjmarket.infrastructure.identity;
import cn.zj.zjmarket.application.identity.*;
import cn.zj.zjmarket.domain.identity.*;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.dao.DuplicateKeyException;
import java.util.*;
import java.util.function.Supplier;
public final class MyBatisIdentityStore implements IdentityStore {
    private final IdentityMapper mapper;
    private final TransactionTemplate tx;
    public MyBatisIdentityStore(IdentityMapper mapper,TransactionTemplate tx){this.mapper=mapper;this.tx=tx;}
    public <T>T transaction(Supplier<T> work){return tx.execute(status -> work.get());}
    private User user(IdentityMapper.UserRow row) {return row==null?null:new User(row.userId(),row.loginName(),row.displayName(),row.passwordHash(),row.enabled(),row.authVersion(),new HashSet<>(mapper.roles(row.userId())));}
    public User userByLogin(String login){return user(mapper.byLogin(login));}
    public User userById(String id){return user(mapper.byId(id));}
    public User lockUser(String id){return user(mapper.lockUser(id));}
    public void insertUser(User user){try{mapper.insertUser(user);user.roles().forEach(role -> mapper.insertRole(user.userId(),role));}catch(DuplicateKeyException e){throw new AuthFailure(409,"LOGIN_NAME_UNAVAILABLE");}}
    public LoginGrant grant(String id){return mapper.grant(id);}
    public LoginGrant lockGrant(String id){return mapper.lockGrant(id);}
    public void insertGrant(LoginGrant grant){mapper.insertGrant(grant);}
    public void revoke(String id){mapper.revoke(id);}
    public RefreshCredential refresh(String digest){return mapper.refresh(digest);}
    public void insertRefresh(RefreshCredential token){mapper.insertRefresh(token);}
    public void useRefresh(String digest){mapper.useRefresh(digest);}
}
