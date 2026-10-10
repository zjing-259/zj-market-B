package cn.zj.zjmarket.domain.payment.model.valobj;
public record ClosedAttempt(String attemptId,int attemptNo,String requestHash,String transactionId,String state) {}
