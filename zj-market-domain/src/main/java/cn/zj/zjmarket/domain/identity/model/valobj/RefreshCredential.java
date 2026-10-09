package cn.zj.zjmarket.domain.identity.model.valobj;

public record RefreshCredential(String digest, String grantId, boolean used) {}
