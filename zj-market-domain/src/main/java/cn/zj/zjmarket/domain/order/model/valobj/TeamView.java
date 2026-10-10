package cn.zj.zjmarket.domain.order.model.valobj;
public record TeamView(String teamId,String goodsId,String activityId,String status,String version,int targetCount,int reservedCount,int paidCount,String validStartTime,String validEndTime,String serverTime,boolean joinable,String myOrderId) {}
