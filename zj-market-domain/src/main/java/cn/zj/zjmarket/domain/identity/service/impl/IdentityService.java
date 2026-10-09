package cn.zj.zjmarket.domain.identity.service.impl;

import cn.zj.zjmarket.domain.identity.adapter.port.IAccessTokenPort;
import cn.zj.zjmarket.domain.identity.adapter.port.IPasswordPort;
import cn.zj.zjmarket.domain.identity.adapter.repository.IIdentityRepository;
import cn.zj.zjmarket.domain.identity.model.entity.LoginGrant;
import cn.zj.zjmarket.domain.identity.model.entity.User;
import cn.zj.zjmarket.domain.identity.model.valobj.AccessTokenClaims;
import cn.zj.zjmarket.domain.identity.model.valobj.AuthenticatedPrincipal;
import cn.zj.zjmarket.domain.identity.model.valobj.IdentityTokens;
import cn.zj.zjmarket.domain.identity.model.valobj.RefreshCredential;
import cn.zj.zjmarket.domain.identity.model.valobj.UserView;
import cn.zj.zjmarket.domain.identity.service.IIdentityService;
import cn.zj.zjmarket.types.exception.AuthFailure;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.time.Clock;
import java.util.*;
public final class IdentityService implements IIdentityService {
    private final IIdentityRepository store;
    private final IPasswordPort passwords;
    private final IAccessTokenPort tokens;
    private final Clock clock;
    private final long accessSeconds, refreshSeconds;
    private final String dummyHash;
    private final SecureRandom random = new SecureRandom();
    public IdentityService(IIdentityRepository store, IPasswordPort passwords, IAccessTokenPort tokens, Clock clock,
                           long accessSeconds, long refreshSeconds) {
        this.store=store;this.passwords=passwords;this.tokens=tokens;this.clock=clock;
        this.accessSeconds=accessSeconds;this.refreshSeconds=refreshSeconds;
        this.dummyHash=passwords.encode(UUID.randomUUID().toString());
    }
    public UserView register(String loginName, String password, String displayName) {
        if(displayName==null)throw failure(400,"VALIDATION_FAILED");
        validate(loginName,password,displayName);
        var user=new User(id(),loginName,displayName,passwords.encode(password),true,1,Set.of("USER"));
        return store.transaction(() -> {store.insertUser(user);return user.view();});
    }
    public UserView initializeOperator(String loginName,String password,String displayName) {
        if(displayName==null)throw failure(400,"VALIDATION_FAILED");
        validate(loginName,password,displayName);
        var user=new User(id(),loginName,displayName,passwords.encode(password),true,1,Set.of("USER","OPERATOR"));
        return store.transaction(() -> {store.insertUser(user);return user.view();});
    }
    public IdentityTokens login(String loginName, String password) {
        validate(loginName,password,null);
        User found=store.userByLogin(loginName);
        boolean valid=passwords.matches(password,found==null?dummyHash:found.passwordHash());
        if(!valid || found==null || !found.enabled()) throw failure(401,"INVALID_CREDENTIALS");
        return store.transaction(() -> {
            User user=store.lockUser(found.userId());
            if(user==null || !user.enabled() || user.authVersion()!=found.authVersion()) throw failure(401,"INVALID_CREDENTIALS");
            long now=now();
            LoginGrant grant=new LoginGrant(id(),user.userId(),user.authVersion(),now+refreshSeconds,false);
            store.insertGrant(grant);
            return rotate(user,grant,now);
        });
    }
    public IdentityTokens refresh(String raw) {
        String digest=digest(raw);
        // Resolve without a row lock, then always lock user -> grant to avoid deadlocks.
        RefreshCredential initial=store.refresh(digest);
        if(initial==null) throw failure(401,"TOKEN_INVALID");
        LoginGrant initialGrant=store.grant(initial.grantId());
        if(initialGrant==null) throw failure(401,"TOKEN_INVALID");
        IdentityTokens result=store.transaction(() -> {
            User user=store.lockUser(initialGrant.userId());
            LoginGrant grant=store.lockGrant(initial.grantId());
            RefreshCredential old=store.refresh(digest);
            if(old==null || grant==null || grant.revoked()) return null;
            if(old.used() || !active(user,grant)) {store.revoke(grant.grantId());return null;}
            store.useRefresh(digest);
            return rotate(user,grant,now());
        });
        // Throw only AFTER the transaction commits replay revocation.
        if(result==null) throw failure(401,"TOKEN_INVALID");
        return result;
    }
    private IdentityTokens rotate(User user,LoginGrant grant,long now) {
        String refresh=randomToken();
        store.insertRefresh(new RefreshCredential(digest(refresh),grant.grantId(),false));
        long expiry=Math.min(now+accessSeconds,grant.expiresAt());
        String jwt=tokens.issue(user,grant,now,expiry);
        return new IdentityTokens(jwt,"Bearer",expiry-now,user.view(),refresh,grant.expiresAt()-now);
    }
    public AuthenticatedPrincipal authenticate(String jwt) {
        AccessTokenClaims claims=tokens.verify(jwt);
        LoginGrant grant=store.grant(claims.grantId());
        User user=store.userById(claims.userId());
        if(grant==null || !grant.userId().equals(claims.userId()) || !active(user,grant)
                || user.authVersion()!=claims.authVersion()) throw failure(401,"TOKEN_INVALID");
        return new AuthenticatedPrincipal(user.view(),grant.grantId());
    }
    public void logout(String access,String refresh) {
        String grantId=null;
        if(access!=null) {
            try {grantId=tokens.verify(access).grantId();}
            catch(AuthFailure ignored) { /* Expired/invalid access may fall back to cookie. */ }
        }
        if(grantId==null && refresh!=null && !refresh.isBlank()) {
            try {var credential=store.refresh(digest(refresh)); if(credential!=null)grantId=credential.grantId();}
            catch(AuthFailure ignored) { /* Idempotent invalid-cookie logout. */ }
        }
        if(grantId!=null) {String target=grantId;store.transaction(() -> {store.revoke(target);return null;});}
    }
    private boolean active(User user,LoginGrant grant) {
        return user!=null && user.enabled() && !grant.revoked() && grant.expiresAt()>now()
                && user.authVersion()==grant.authVersion();
    }
    public static void validate(String login,String password,String display) {
        if(login==null || !login.matches("^[a-z0-9][a-z0-9._-]{2,31}$") || password==null
            || password.codePointCount(0,password.length())<12 || password.codePointCount(0,password.length())>64
            || (display!=null && (display.isBlank() || display.codePointCount(0,display.length())>64)))
            throw failure(400,"VALIDATION_FAILED");
    }
    private long now(){return clock.instant().getEpochSecond();}
    private static String id(){return UUID.randomUUID().toString();}
    private String randomToken(){byte[] bytes=new byte[32];random.nextBytes(bytes);return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);}
    private static String digest(String raw) {
        if(raw==null || !raw.matches("^[A-Za-z0-9_-]{43}$")) throw failure(401,"TOKEN_INVALID");
        try {return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw.getBytes(StandardCharsets.US_ASCII)));}
        catch(NoSuchAlgorithmException e){throw new IllegalStateException(e);}
    }
    private static AuthFailure failure(int status,String code){return new AuthFailure(status,code);}


}
