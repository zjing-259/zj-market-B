package cn.zj.zjmarket.domain.order.model.valobj;
public record DiscoveryItem(String teamId,int targetCount,int reservedCount,int paidCount,int availableSlots,int remainingPaidCount,String validEndTime) {}
