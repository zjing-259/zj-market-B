package cn.zj.zjmarket.application.product;
import cn.zj.zjmarket.domain.product.*;
import java.math.BigDecimal;
import java.time.Instant;
/** Two separate local read transactions surround a network call; never hold a DB transaction during RPC. */
public final class MarketingTrialService {
    private final ProductService products;
    private final MarketingTrialPort marketing;
    public MarketingTrialService(ProductService products,MarketingTrialPort marketing){this.products=products;this.marketing=marketing;}
    public record Result(String goodsId,String productVersion,String quotedAt,String state,MarketingTrialPort.Offer offer) {}
    public Result trial(String userId,String goodsId,String requestId){
        if(userId==null || userId.isBlank() || userId.length()>64)throw new ProductFailure(401,"AUTH_REQUIRED");
        var before=products.detail(goodsId,false);
        if(!before.sync().ready(before.product().version()))throw new ProductFailure(409,"PRODUCT_SYNC_PENDING");
        var quote=marketing.trial(userId,before.product(),requestId);
        var after=products.detail(goodsId,true);
        if(after.product().version()!=before.product().version() || after.product().fields().saleStatus()!=Product.SaleStatus.ON_SALE || !after.sync().targetEventId().equals(before.sync().targetEventId()))throw new ProductFailure(409,"PRODUCT_VERSION_MISMATCH");
        if(!after.sync().ready(after.product().version()))throw new ProductFailure(409,"PRODUCT_SYNC_PENDING");
        return validate(before.product(),quote);
    }
    private static Result validate(Product p,MarketingTrialPort.Quote q){
        try{
            if(q==null || q.available()==null || q.visible()==null || q.eligible()==null || q.quotedAt()==null || !q.quotedAt().matches("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{3}Z"))throw invalid();
            Instant.parse(q.quotedAt());
            if(!q.available() || !q.visible())return new Result(p.goodsId(),Long.toString(p.version()),q.quotedAt(),"NO_PUBLIC_OFFER",null);
            var offer=q.offer();if(q.eligible() && offer==null)throw invalid();
            if(offer!=null){
                Product.parseVersion(offer.activityId());
                if(!p.goodsId().equals(offer.goodsId()) || !Long.toString(p.version()).equals(offer.productVersion()) || !"CNY".equals(offer.currency()) || offer.targetCount()==null || offer.targetCount()<1 || offer.targetCount()>100)throw invalid();
                BigDecimal original=money(offer.originalPrice(),false),deduction=money(offer.deductionPrice(),true),pay=money(offer.payPrice(),false);
                if(original.compareTo(p.fields().originalPrice())!=0 || original.subtract(deduction).compareTo(pay)!=0)throw invalid();
            }
            return new Result(p.goodsId(),Long.toString(p.version()),q.quotedAt(),q.eligible()?"AVAILABLE":"INELIGIBLE",offer);
        }catch(ProductFailure failure){throw failure;}catch(Exception invalid){throw invalid();}
    }
    private static BigDecimal money(String value,boolean zero){
        if(value==null || !value.matches("(?:0|[1-9][0-9]{0,5})\\.[0-9]{2}"))throw invalid();
        var amount=new BigDecimal(value);if(amount.compareTo(zero?BigDecimal.ZERO:new BigDecimal("0.01"))<0 || amount.compareTo(new BigDecimal("999999.99"))>0)throw invalid();return amount;
    }
    private static ProductFailure invalid(){return new ProductFailure(502,"UPSTREAM_RESPONSE_INVALID");}
}
