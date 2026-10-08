package cn.zj.zjmarket.infrastructure.identity;
import cn.zj.zjmarket.application.identity.*;
import cn.zj.zjmarket.domain.identity.*;
import com.nimbusds.jose.*;
import com.nimbusds.jose.crypto.*;
import com.nimbusds.jwt.*;
import java.nio.file.*;
import java.security.*;
import java.security.interfaces.*;
import java.security.spec.*;
import java.time.Clock;
import java.util.*;
public final class RsaAccessTokens implements AccessTokenPort {
    private final IdentitySettings settings;
    private final Clock clock;
    private final RSAPrivateKey privateKey;
    private final Map<String,RSAPublicKey> keys=new HashMap<>();
    public RsaAccessTokens(IdentitySettings settings,Clock clock) throws Exception {
        this.settings=settings;this.clock=clock;settings.validate();
        var factory=KeyFactory.getInstance("RSA");
        privateKey=(RSAPrivateKey)factory.generatePrivate(new PKCS8EncodedKeySpec(pem(settings.getPrivateKeyFile(),"PRIVATE KEY")));
        var current=(RSAPublicKey)factory.generatePublic(new X509EncodedKeySpec(pem(settings.getPublicKeyFile(),"PUBLIC KEY")));
        if(privateKey.getModulus().bitLength()<2048 || !privateKey.getModulus().equals(current.getModulus())) throw new IllegalArgumentException("RSA key pair mismatch or too small");
        keys.put(settings.getKeyId(),current);
        if(!settings.getPreviousPublicKeys().isBlank()) for(String item:settings.getPreviousPublicKeys().split(";")) {
            String[] parts=item.split("=",2);
            if(parts.length!=2 || !parts[0].matches("[A-Za-z0-9_-]{1,64}") || keys.containsKey(parts[0])) throw new IllegalArgumentException("Invalid public key allowlist");
            var key=(RSAPublicKey)factory.generatePublic(new X509EncodedKeySpec(pem(parts[1],"PUBLIC KEY")));
            if(key.getModulus().bitLength()<2048) throw new IllegalArgumentException("RSA key too small");keys.put(parts[0],key);
        }
    }
    private static byte[] pem(String path,String type)throws Exception{
        return Base64.getDecoder().decode(Files.readString(Path.of(path)).replace("-----BEGIN "+type+"-----","").replace("-----END "+type+"-----","").replaceAll("\\s", ""));
    }
    public String issue(User user,LoginGrant grant,long now,long expiry){
        try {
            var claims=new JWTClaimsSet.Builder().issuer(settings.getIssuer()).audience(settings.getAudience()).subject(user.userId())
                .jwtID(UUID.randomUUID().toString()).issueTime(new Date(now*1000)).notBeforeTime(new Date(now*1000)).expirationTime(new Date(expiry*1000))
                .claim("sid",grant.grantId()).claim("av",user.authVersion()).build();
            var jwt=new SignedJWT(new JWSHeader.Builder(JWSAlgorithm.RS256).type(JOSEObjectType.JWT).keyID(settings.getKeyId()).build(),claims);
            jwt.sign(new RSASSASigner(privateKey));return jwt.serialize();
        }catch(Exception e){throw new AuthFailure(503,"DEPENDENCY_UNAVAILABLE");}
    }
    public Claims verify(String raw){
        try {
            if(raw==null || raw.length()>8192) throw new IllegalArgumentException();
            var jwt=SignedJWT.parse(raw);var h=jwt.getHeader();
            var key=keys.get(h.getKeyID());
            if(!JWSAlgorithm.RS256.equals(h.getAlgorithm()) || !JOSEObjectType.JWT.equals(h.getType()) || key==null
                || h.getJWKURL()!=null || h.getJWK()!=null || (h.getCriticalParams()!=null && !h.getCriticalParams().isEmpty())
                || !jwt.verify(new RSASSAVerifier(key))) throw new IllegalArgumentException();
            var c=jwt.getJWTClaimsSet();long now=clock.instant().getEpochSecond();
            if(c.getExpirationTime()==null || c.getIssueTime()==null || c.getNotBeforeTime()==null || c.getJWTID()==null
                || c.getSubject()==null || !c.getSubject().matches("[A-Za-z0-9_-]{1,64}") || !settings.getIssuer().equals(c.getIssuer())
                || !List.of(settings.getAudience()).equals(c.getAudience()) || c.getStringClaim("sid")==null
                || c.getStringClaim("sid").isBlank() || c.getStringClaim("sid").length()>64 || c.getJWTID().isBlank()
                || c.getLongClaim("av")==null || c.getLongClaim("av")<1 || c.getIssueTime().getTime()/1000>now+30 || c.getNotBeforeTime().getTime()/1000>now+30
                || c.getExpirationTime().before(c.getIssueTime())
                || c.getExpirationTime().getTime()-c.getIssueTime().getTime()>settings.getAccessSeconds()*1000)
                throw new IllegalArgumentException();
            if(c.getExpirationTime().getTime()/1000<=now) throw new AuthFailure(401,"TOKEN_EXPIRED");
            return new Claims(c.getSubject(),c.getStringClaim("sid"),c.getLongClaim("av"));
        }catch(AuthFailure e){throw e;}catch(Exception e){throw new AuthFailure(401,"TOKEN_INVALID");}
    }
}
