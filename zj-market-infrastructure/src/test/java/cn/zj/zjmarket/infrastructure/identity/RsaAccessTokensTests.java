package cn.zj.zjmarket.infrastructure.identity;
import cn.zj.zjmarket.application.identity.AuthFailure;
import cn.zj.zjmarket.domain.identity.*;
import com.nimbusds.jose.*;
import com.nimbusds.jose.crypto.*;
import com.nimbusds.jwt.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import java.security.*;
import java.security.interfaces.*;
import java.nio.file.*;
import java.time.*;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
class RsaAccessTokensTests {
    @TempDir Path directory;
    KeyPair pair;IdentitySettings settings;RsaAccessTokens tokens;
    long now=Instant.parse("2026-10-08T00:00:00Z").getEpochSecond();
    @BeforeEach void setup()throws Exception{
        var generator=KeyPairGenerator.getInstance("RSA");generator.initialize(2048);pair=generator.generateKeyPair();
        settings=settings(pair,"current");tokens=new RsaAccessTokens(settings,Clock.fixed(Instant.ofEpochSecond(now),ZoneOffset.UTC));
    }
    IdentitySettings settings(KeyPair keys,String kid)throws Exception{
        var s=new IdentitySettings();s.setOrigin("https://market.example.test");s.setKeyId(kid);
        var privatePath=directory.resolve(kid+"-private.pem");var publicPath=directory.resolve(kid+"-public.pem");
        Files.writeString(privatePath,"-----BEGIN PRIVATE KEY-----\n"+Base64.getMimeEncoder().encodeToString(keys.getPrivate().getEncoded())+"\n-----END PRIVATE KEY-----");
        Files.writeString(publicPath,"-----BEGIN PUBLIC KEY-----\n"+Base64.getMimeEncoder().encodeToString(keys.getPublic().getEncoded())+"\n-----END PUBLIC KEY-----");
        s.setPrivateKeyFile(privatePath.toString());s.setPublicKeyFile(publicPath.toString());return s;
    }
    JWTClaimsSet.Builder claims(){return new JWTClaimsSet.Builder().issuer("zj-market").audience("zj-market-web").subject("user-1").jwtID("token-1")
        .issueTime(new Date(now*1000)).notBeforeTime(new Date(now*1000)).expirationTime(new Date((now+900)*1000)).claim("sid","grant-1").claim("av",1L);}
    String signed(JWTClaimsSet claims)throws Exception{return signed(claims,new JWSHeader.Builder(JWSAlgorithm.RS256).type(JOSEObjectType.JWT).keyID("current").build());}
    String signed(JWTClaimsSet claims,JWSHeader header)throws Exception{var jwt=new SignedJWT(header,claims);jwt.sign(new RSASSASigner((RSAPrivateKey)pair.getPrivate()));return jwt.serialize();}
    void reject(String jwt){assertEquals(401,assertThrows(AuthFailure.class,()->tokens.verify(jwt)).status());}
    @Test void actualRsaRoundTrip(){var jwt=tokens.issue(new User("user-1","user","User","unused",true,1,Set.of("USER")),new LoginGrant("grant-1","user-1",1,now+604800,false),now,now+900);
        assertEquals("user-1",tokens.verify(jwt).userId());assertEquals("grant-1",tokens.verify(jwt).grantId());}
    @Test void rejectsIssuerAudienceAndMissingClaims()throws Exception{
        reject(signed(claims().issuer("foreign").build()));reject(signed(claims().audience("other").build()));
        reject(signed(claims().claim("sid",null).build()));reject(signed(claims().claim("av",null).build()));
        reject(signed(claims().jwtID(null).build()));reject(signed(claims().notBeforeTime(null).build()));reject(signed(claims().issueTime(null).build()));
    }
    @Test void rejectsExpiryFutureAndExtendedLifetime()throws Exception{
        var expired=signed(claims().issueTime(new Date((now-900)*1000)).expirationTime(new Date(now*1000)).build());
        assertEquals("TOKEN_EXPIRED",assertThrows(AuthFailure.class,()->tokens.verify(expired)).code());
        reject(signed(claims().notBeforeTime(new Date((now+31)*1000)).build()));
        reject(signed(claims().issueTime(new Date((now+31)*1000)).build()));
        reject(signed(claims().expirationTime(new Date((now+901)*1000)).build()));
    }
    @Test void rejectsNoneHmacAlgorithmConfusionTamperAndUnknownKey()throws Exception{
        reject(new PlainJWT(claims().build()).serialize());
        var jwt=new SignedJWT(new JWSHeader(JWSAlgorithm.HS256),claims().build());jwt.sign(new MACSigner(pair.getPublic().getEncoded()));reject(jwt.serialize());
        reject(signed(claims().build(),new JWSHeader.Builder(JWSAlgorithm.RS256).type(JOSEObjectType.JWT).keyID("unknown").build()));
        String valid=signed(claims().build());String[] segments=valid.split("\\.");
        segments[1]=Base64.getUrlEncoder().withoutPadding().encodeToString(claims().subject("attacker").build().toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));reject(String.join(".",segments));
    }
    @Test void rejectsRemoteJwkAndWrongRsaSignature()throws Exception{
        reject(signed(claims().build(),new JWSHeader.Builder(JWSAlgorithm.RS256).type(JOSEObjectType.JWT).keyID("current").jwkURL(java.net.URI.create("https://evil.test/key")).build()));
        var generator=KeyPairGenerator.getInstance("RSA");generator.initialize(2048);var other=generator.generateKeyPair();
        var jwt=new SignedJWT(new JWSHeader.Builder(JWSAlgorithm.RS256).type(JOSEObjectType.JWT).keyID("current").build(),claims().build());jwt.sign(new RSASSASigner((RSAPrivateKey)other.getPrivate()));reject(jwt.serialize());
    }
    @Test void externalPublicKeyRotationWorksWithoutOldPrivateKey()throws Exception{
        var old=signed(claims().build());var generator=KeyPairGenerator.getInstance("RSA");generator.initialize(2048);
        var next=settings(generator.generateKeyPair(),"next");next.setPreviousPublicKeys("current="+settings.getPublicKeyFile());
        var rotated=new RsaAccessTokens(next,Clock.fixed(Instant.ofEpochSecond(now),ZoneOffset.UTC));assertEquals("user-1",rotated.verify(old).userId());
        next.setPreviousPublicKeys("");var retired=new RsaAccessTokens(next,Clock.fixed(Instant.ofEpochSecond(now),ZoneOffset.UTC));assertThrows(AuthFailure.class,()->retired.verify(old));
    }
    @Test void insecureCookieExceptionOnlyAllowsLoopback(){settings.setSecureCookies(false);assertThrows(IllegalArgumentException.class,()->settings.validate());settings.setOrigin("http://127.0.0.1:5173");assertDoesNotThrow(()->settings.validate());settings.setOrigin("http://public.test");assertThrows(IllegalArgumentException.class,()->settings.validate());}
}
