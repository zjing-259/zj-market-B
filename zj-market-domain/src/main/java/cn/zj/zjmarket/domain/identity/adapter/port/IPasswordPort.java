package cn.zj.zjmarket.domain.identity.adapter.port;

public interface IPasswordPort {
    String encode(String password);
    boolean matches(String password, String hash);
}
