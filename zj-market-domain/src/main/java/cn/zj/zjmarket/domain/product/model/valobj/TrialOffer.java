package cn.zj.zjmarket.domain.product.model.valobj;

public record TrialOffer(String activityId,String goodsId,String productVersion,String originalPrice,String deductionPrice,String payPrice,String currency,Integer targetCount) {}
