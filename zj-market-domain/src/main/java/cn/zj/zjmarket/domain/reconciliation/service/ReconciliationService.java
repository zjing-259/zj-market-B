package cn.zj.zjmarket.domain.reconciliation.service;
import cn.zj.zjmarket.domain.reconciliation.adapter.port.IReconciliationPort;
import cn.zj.zjmarket.domain.reconciliation.adapter.repository.IReconciliationRepository;
import cn.zj.zjmarket.domain.payment.adapter.port.IChannelFacts;
import cn.zj.zjmarket.domain.payment.adapter.repository.ISettlementRepository;
import cn.zj.zjmarket.domain.reconciliation.model.Reconciliation.*;
import cn.zj.zjmarket.types.exception.OrderFailure;

/** One member per lease: no full-roster network loop under a 30 second lease. */
public final class ReconciliationService {
 private final IReconciliationRepository repo;private final IReconciliationPort port;private final IChannelFacts channel;private final ISettlementRepository settlement;
 public ReconciliationService(IReconciliationRepository repo,IReconciliationPort port,IChannelFacts channel,ISettlementRepository settlement){this.repo=repo;this.port=port;this.channel=channel;this.settlement=settlement;}
 public void tick(int size,boolean discover){if(discover)try{repo.discover(size);}catch(RuntimeException unavailable){System.getLogger(getClass().getName()).log(System.Logger.Level.WARNING,"Discovery pending; existing recovery continues");}for(String id:repo.due(size))try{recover(id);}catch(RuntimeException unavailable){System.getLogger(getClass().getName()).log(System.Logger.Level.WARNING,"One task unavailable; unrelated recovery continues");}}
 public void recover(String id){var lease=repo.claim(id);if(lease==null)return;try{
  var team=port.team(lease.teamId());team.validate(lease.teamId());
  if("COMPLETED".equals(team.status())){repo.terminal(lease,team);return;}
  if("FORMING".equals(team.status())){repo.defer(lease,"RECONCILIATION_NOT_STARTED",false);return;}
  if(!repo.hasRoster(lease)){var roster=port.roster(lease.teamId());roster.validate();repo.saveRoster(lease,team,roster);return;}
  // A lost completion response must be recovered by the original request, even if A is now FAILED.
  var frozen=repo.submission(lease,team);
  if(frozen!=null){var result=port.complete(frozen);result.validate(frozen);repo.acknowledge(lease,frozen,result);return;}
  if("FAILED".equals(team.status())){repo.terminal(lease,team);return;}
  var member=repo.nextMember(lease);if(member==null){repo.defer(lease,"MEMBER_DEPENDENCY_PENDING",false);return;}
  var local=repo.prepare(lease,member);if(local==null){repo.defer(lease,"MISSING_LOCAL_MEMBER",false);return;}
  if(local.paymentId()!=null)for(String attempt:local.attemptIds()){var fact=channel.fact(local.paymentId(),attempt);if(fact!=null)settlement.observe(fact);}
  var observed=port.trade(local.order());observed.validate(local.order());
  boolean close=repo.observe(lease,member,observed);
  if(close)repo.closeUnpaid(local.order().orderId());
 }catch(IllegalArgumentException invalid){repo.defer(lease,"RECONCILIATION_EVIDENCE_CONFLICT",true);}
 catch(OrderFailure failure){boolean conflict=java.util.Set.of("RECONCILIATION_CONFLICT","UPSTREAM_RESPONSE_INVALID","FORBIDDEN","INTEGRATION_AUTH_FAILED","LEGACY_FACT_UNVERIFIABLE").contains(failure.code());repo.defer(lease,failure.code(),conflict);}
 catch(RuntimeException unavailable){repo.defer(lease,"RECONCILIATION_DEPENDENCY_UNAVAILABLE",false);}}
}
