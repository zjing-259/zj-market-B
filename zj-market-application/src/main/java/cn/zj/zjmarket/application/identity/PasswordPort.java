package cn.zj.zjmarket.application.identity;
public interface PasswordPort {
    String encode(String password);
    boolean matches(String password, String hash);
}
