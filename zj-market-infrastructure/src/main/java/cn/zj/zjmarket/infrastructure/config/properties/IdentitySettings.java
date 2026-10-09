package cn.zj.zjmarket.infrastructure.config.properties;

import org.springframework.boot.context.properties.ConfigurationProperties;
@ConfigurationProperties("b.identity")
public class IdentitySettings {
    private boolean enabled,secureCookies=true;
    private String issuer="zj-market",audience="zj-market-web",keyId,privateKeyFile,publicKeyFile,previousPublicKeys="",origin;
    private long accessSeconds=900,refreshSeconds=604800;
    public boolean isEnabled(){return enabled;} public void setEnabled(boolean v){enabled=v;}
    public boolean isSecureCookies(){return secureCookies;}public void setSecureCookies(boolean v){secureCookies=v;}
    public String getIssuer(){return issuer;}public void setIssuer(String v){issuer=v;}
    public String getAudience(){return audience;}public void setAudience(String v){audience=v;}
    public String getKeyId(){return keyId;}public void setKeyId(String v){keyId=v;}
    public String getPrivateKeyFile(){return privateKeyFile;}public void setPrivateKeyFile(String v){privateKeyFile=v;}
    public String getPublicKeyFile(){return publicKeyFile;}public void setPublicKeyFile(String v){publicKeyFile=v;}
    public String getPreviousPublicKeys(){return previousPublicKeys;}public void setPreviousPublicKeys(String v){previousPublicKeys=v;}
    public String getOrigin(){return origin;}public void setOrigin(String v){origin=v;}
    public long getAccessSeconds(){return accessSeconds;}public void setAccessSeconds(long v){accessSeconds=v;}
    public long getRefreshSeconds(){return refreshSeconds;}public void setRefreshSeconds(long v){refreshSeconds=v;}
    public void validate(){
        if(origin==null || !origin.matches("https?://[^/]+") || keyId==null || !keyId.matches("[A-Za-z0-9_-]{1,64}")
            || privateKeyFile==null || publicKeyFile==null || issuer==null || issuer.isBlank() || audience==null || audience.isBlank()
            || accessSeconds<1 || accessSeconds>900 || refreshSeconds<accessSeconds || refreshSeconds>604800)
            throw new IllegalArgumentException("Invalid external identity configuration");
        if(secureCookies && !origin.startsWith("https://")) throw new IllegalArgumentException("Secure cookies require HTTPS origin");
        if(!secureCookies && !origin.matches("http://(localhost|127\\.0\\.0\\.1)(:[0-9]+)?")) throw new IllegalArgumentException("Insecure cookies only allowed on explicit loopback development origin");
    }
}
