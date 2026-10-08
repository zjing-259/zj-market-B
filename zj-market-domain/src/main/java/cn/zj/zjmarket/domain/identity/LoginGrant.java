package cn.zj.zjmarket.domain.identity;
public record LoginGrant(String grantId, String userId, long authVersion, long expiresAt, boolean revoked) {}
