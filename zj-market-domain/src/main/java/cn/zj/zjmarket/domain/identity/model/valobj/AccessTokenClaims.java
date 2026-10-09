package cn.zj.zjmarket.domain.identity.model.valobj;

public record AccessTokenClaims(String userId, String grantId, long authVersion) {}
