package cn.zj.zjmarket.domain.order.model.valobj;
public record TradeReply(String code,ReservationEvidence evidence,CloseEvidence closeEvidence){public TradeReply(String code,ReservationEvidence evidence){this(code,evidence,null);}}
