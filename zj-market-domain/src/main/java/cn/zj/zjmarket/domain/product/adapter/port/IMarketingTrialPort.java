package cn.zj.zjmarket.domain.product.adapter.port;

import cn.zj.zjmarket.domain.product.model.entity.Product;
import cn.zj.zjmarket.domain.product.model.valobj.TrialQuote;
/** A contract DTOs and RPC dependencies never cross this application boundary. */
public interface IMarketingTrialPort {
    TrialQuote trial(String userId,Product product,String requestId);


}
