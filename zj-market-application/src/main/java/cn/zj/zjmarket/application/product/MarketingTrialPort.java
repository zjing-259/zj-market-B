package cn.zj.zjmarket.application.product;
import cn.zj.zjmarket.domain.product.Product;
/** A contract DTOs and RPC dependencies never cross this application boundary. */
public interface MarketingTrialPort {
    Quote trial(String userId,Product product,String requestId);
    record Offer(String activityId,String goodsId,String productVersion,String originalPrice,String deductionPrice,String payPrice,String currency,Integer targetCount) {}
    record Quote(Boolean available,Boolean visible,Boolean eligible,String quotedAt,Offer offer) {}
}
