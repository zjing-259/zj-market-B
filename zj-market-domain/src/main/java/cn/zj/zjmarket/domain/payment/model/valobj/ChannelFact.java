package cn.zj.zjmarket.domain.payment.model.valobj;
public record ChannelFact(Channel channel,String snapshotHash,String requestHash,String gate,String successAttemptId,long reservedAt,long deadline){}
