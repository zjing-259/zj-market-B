package cn.zj.zjmarket.domain.product.model.valobj;

public record TrialQuote(Boolean available,Boolean visible,Boolean eligible,String quotedAt,TrialOffer offer) {}
