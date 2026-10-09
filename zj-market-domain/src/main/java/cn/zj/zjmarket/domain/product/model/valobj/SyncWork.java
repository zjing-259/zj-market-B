package cn.zj.zjmarket.domain.product.model.valobj;

import java.util.*;
public record SyncWork(String eventId,String goodsId,long version,String saleStatus,String body,String bodyHash,String deliveryState,int sendAttempts,int sendFailures,int queryAttempts,String leaseToken,String processingState,boolean paused){}
