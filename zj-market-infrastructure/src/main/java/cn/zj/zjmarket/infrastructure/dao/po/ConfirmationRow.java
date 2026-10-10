package cn.zj.zjmarket.infrastructure.dao.po;
public record ConfirmationRow(String confirmationId,String userId,String source,String channel,String goodsId,long productVersion,long activityId,String mode,String teamId,String snapshot,long issuedAt,long expiresAt,Long boundAt) {}
