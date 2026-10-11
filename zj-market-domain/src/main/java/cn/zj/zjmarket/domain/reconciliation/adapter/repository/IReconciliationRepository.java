package cn.zj.zjmarket.domain.reconciliation.adapter.repository;
import cn.zj.zjmarket.domain.reconciliation.model.Reconciliation.*;
import java.util.List;
public interface IReconciliationRepository {
 void discover(int size);
 List<String> due(int size);
 Lease claim(String taskId);
 boolean hasRoster(Lease lease);
 void saveRoster(Lease lease,Team team,Roster roster);
 Member nextMember(Lease lease);
 Local prepare(Lease lease,Member member);
 boolean observe(Lease lease,Member member,Trade trade);
 void closeUnpaid(String orderId);
 Completion submission(Lease lease,Team team);
 void acknowledge(Lease lease,Completion completion,Result result);
 void terminal(Lease lease,Team team);
 void defer(Lease lease,String error,boolean conflict);
}
