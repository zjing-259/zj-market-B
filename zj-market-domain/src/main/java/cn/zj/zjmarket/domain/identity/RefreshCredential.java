package cn.zj.zjmarket.domain.identity;
public record RefreshCredential(String digest, String grantId, boolean used) {}
