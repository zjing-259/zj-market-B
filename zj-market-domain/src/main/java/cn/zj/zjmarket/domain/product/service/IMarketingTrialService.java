package cn.zj.zjmarket.domain.product.service;

import cn.zj.zjmarket.domain.product.model.valobj.TrialResult;
public interface IMarketingTrialService { TrialResult trial(String userId,String goodsId,String requestId); }
