package cn.zj.zjmarket.domain.identity.model.entity;

public record LoginGrant(String grantId, String userId, long authVersion, long expiresAt, boolean revoked) {}
