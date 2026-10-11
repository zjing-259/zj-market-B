package cn.zj.zjmarket.domain.refund.adapter.repository;
import java.util.Map;
public interface IRefundOperations {
 record Control(String operationId,String action,long expectedVersion,String reason){}
 record Result(boolean replay,Map<String,Object> result){}
 Map<String,Object> refunds(String actor,Map<String,String> filters);
 Map<String,Object> refund(String actor,String refundId);
 Map<String,Object> reconciliations(String actor,Map<String,String> filters);
 Map<String,Object> reconciliation(String actor,String taskId);
 Result control(String actor,String refundId,Control control);
}
