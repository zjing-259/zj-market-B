package cn.zj.zjmarket.domain.product.model.valobj;

public record SyncResult(String receiptId,String producer,String receiptHash,String originalEventId,String outcome,String code,String processedAt,String goodsId,String currentVersion,Boolean applied,String saleStatus,String factHash){}
