package cn.zj.zjmarket.application.identity;
import cn.zj.zjmarket.domain.identity.*;
import java.time.Clock;
import java.security.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
public final class IdentityService {
    private final IdentityStore store;
    private final PasswordPort passwords;
    private final AccessTokenPort tokens;
    private final Clock clock;
    private final long accessSeconds, refreshSeconds;
    private final String dummyHash;
    private final SecureRandom random = new SecureRandom();
    public IdentityService(IdentityStore store, PasswordPort passwords, AccessTokenPort tokens, Clock clock,
                           long accessSeconds, long refreshSeconds) {
        this.store=store;this.passwords=passwords;this.tokens=tokens;this.clock=clock;
        this.accessSeconds=accessSeconds;this.refreshSeconds=refreshSeconds;
        this.dummyHash=passwords.encode(UUID.randomUUID().toString());
    }
    public User.View register(String loginName, String password, String displayName) {
        if(displayName==null)throw failure(400,"VALIDATION_FAILED");
        validate(loginName,password,displayName);
        var user=new User(id(),loginName,displayName,passwords.encode(password),true,1,Set.of("USER"));
        return store.transaction(() -> {store.insertUser(user);return user.view();});
    }
    public User.View initializeOperator(String loginName,String password,String displayName) {
        if(displayName==null)throw failure(400,"VALIDATION_FAILED");
        validate(loginName,password,displayName);
        var user=new User(id(),loginName,displayName,passwords.encode(password),true,1,Set.of("USER","OPERATOR"));
        return store.transaction(() -> {store.insertUser(user);return user.view();});
    }
    public Tokens login(String loginName, String password) {
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
    public Tokens refresh(String raw) {
        String digest=digest(raw);
        // Resolve without a row lock, then always lock user -> grant to avoid deadlocks.
        RefreshCredential initial=store.refresh(digest);
        if(initial==null) throw failure(401,"TOKEN_INVALID");
        LoginGrant initialGrant=store.grant(initial.grantId());
        if(initialGrant==null) throw failure(401,"TOKEN_INVALID");
        Tokens result=store.transaction(() -> {
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
    private Tokens rotate(User user,LoginGrant grant,long now) {
        String refresh=randomToken();
        store.insertRefresh(new RefreshCredential(digest(refresh),grant.grantId(),false));
        long expiry=Math.min(now+accessSeconds,grant.expiresAt());
        String jwt=tokens.issue(user,grant,now,expiry);
        return new Tokens(jwt,"Bearer",expiry-now,user.view(),refresh,grant.expiresAt()-now);
    }
    public Principal authenticate(String jwt) {
        AccessTokenPort.Claims claims=tokens.verify(jwt);
        LoginGrant grant=store.grant(claims.grantId());
        User user=store.userById(claims.userId());
        if(grant==null || !grant.userId().equals(claims.userId()) || !active(user,grant)
                || user.authVersion()!=claims.authVersion()) throw failure(401,"TOKEN_INVALID");
        return new Principal(user.view(),grant.grantId());
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
    public record Principal(User.View user,String grantId) {}
    public record Tokens(String accessToken,String tokenType,long expiresIn,User.View user,
                         String refreshToken,long refreshExpiresIn) {}
}
