package cn.zj.zjmarket.domain.payment.model.valobj;
public record ChannelNotice(String id,String paymentId,String attemptId,String body,String hash,String token,Channel observed,int failures){}
