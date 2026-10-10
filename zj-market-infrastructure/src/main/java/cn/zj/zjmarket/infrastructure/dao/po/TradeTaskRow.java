package cn.zj.zjmarket.infrastructure.dao.po;
public record TradeTaskRow(String orderId,String intent,long intentVersion,String runState,boolean paused,long taskVersion,long nextAttempt,String leaseToken,Long leaseUntil,long attemptCount,long failureCount,boolean alerted,boolean authCheckRequired,boolean authProbe,String lastError) {}
