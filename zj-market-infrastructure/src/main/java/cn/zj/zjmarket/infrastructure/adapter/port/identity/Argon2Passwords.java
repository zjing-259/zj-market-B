package cn.zj.zjmarket.infrastructure.adapter.port.identity;

import cn.zj.zjmarket.domain.identity.adapter.port.IPasswordPort;
import cn.zj.zjmarket.types.exception.AuthFailure;
import java.util.Map;
import org.springframework.security.crypto.argon2.Argon2PasswordEncoder;
import org.springframework.security.crypto.password.DelegatingPasswordEncoder;
/** User-selected Argon2id parameters retained from the validated B-02 baseline. */
public final class Argon2Passwords implements IPasswordPort {
 private final DelegatingPasswordEncoder encoder=new DelegatingPasswordEncoder("argon2id",Map.of("argon2id",new Argon2PasswordEncoder(16,32,1,19456,2)));
 public String encode(String raw){return encoder.encode(raw);}
 public boolean matches(String raw,String hash){try{return encoder.matches(raw,hash);}catch(IllegalArgumentException e){throw new AuthFailure(503,"DEPENDENCY_UNAVAILABLE");}}
}
