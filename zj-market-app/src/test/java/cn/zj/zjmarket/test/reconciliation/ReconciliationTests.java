package cn.zj.zjmarket.test.reconciliation;
import cn.zj.zjmarket.domain.reconciliation.model.Reconciliation.*;
import cn.zj.zjmarket.domain.reconciliation.adapter.port.IReconciliationPort;
import cn.zj.zjmarket.domain.reconciliation.adapter.repository.IReconciliationRepository;
import cn.zj.zjmarket.domain.reconciliation.service.ReconciliationService;
import cn.zj.zjmarket.domain.payment.adapter.port.IChannelFacts;
import cn.zj.zjmarket.domain.payment.adapter.repository.ISettlementRepository;
import org.junit.jupiter.api.Test;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
class ReconciliationTests {
 static final String TIME="2026-10-10T12:00:00.000Z";
 final IReconciliationRepository repo=mock(IReconciliationRepository.class);
 final IReconciliationPort port=mock(IReconciliationPort.class);
 final ReconciliationService service=new ReconciliationService(repo,port,mock(IChannelFacts.class),mock(ISettlementRepository.class));
 final Lease lease=new Lease("task","team","token",1);
 Team team(String status){return new Team("team",status,"3","goods","1",TIME,TIME);}
 Member member(){return new Member("user","order","a-order","RESERVED","2026-10-10T11:00:00.000Z",TIME,"9.00","CNY",null);}
 Completion completion(List<Decision> ds){return new Completion("s01","c01","team","recon","roster","completion",TIME,ds);}
 Decision paid(){return new Decision("user","order","PAID_ACCEPTED","payment",null,null,null,null,null);}
 @Test void completedWithoutReconciliationRosterUsesTerminalPath(){when(repo.claim("task")).thenReturn(lease);when(port.team("team")).thenReturn(team("COMPLETED"));service.recover("task");verify(repo).terminal(lease,team("COMPLETED"));verify(port,never()).roster(anyString());verify(repo,never()).submission(any(),any());}
 @Test void formingNeverInventsEmptyFrozenRoster(){when(repo.claim("task")).thenReturn(lease);when(port.team("team")).thenReturn(team("FORMING"));service.recover("task");verify(repo).defer(lease,"RECONCILIATION_NOT_STARTED",false);verify(port,never()).roster(anyString());}
 @Test void failedAfterLostResponseReplaysOriginalCompletionBeforeFinalization(){var c=completion(List.of(paid()));when(repo.claim("task")).thenReturn(lease);when(port.team("team")).thenReturn(team("FAILED"));when(repo.hasRoster(lease)).thenReturn(true);when(repo.submission(lease,team("FAILED"))).thenReturn(c);var result=new Result("team","recon","FAILED","4",TIME);when(port.complete(c)).thenReturn(result);service.recover("task");verify(port).complete(same(c));verify(repo).acknowledge(lease,c,result);verify(repo,never()).terminal(any(),any());}
 @Test void lostCompletionResponseRetainsUnknownOriginalRequest(){var c=completion(List.of(paid()));when(repo.claim("task")).thenReturn(lease);when(port.team("team")).thenReturn(team("RECONCILING"));when(repo.hasRoster(lease)).thenReturn(true);when(repo.submission(any(),any())).thenReturn(c);when(port.complete(c)).thenThrow(new IllegalStateException("response lost"));service.recover("task");verify(repo).defer(lease,"RECONCILIATION_DEPENDENCY_UNAVAILABLE",false);verify(repo,never()).acknowledge(any(),any(),any());}
 @Test void malformedRosterIsQuarantinedBeforePersistence(){when(repo.claim("task")).thenReturn(lease);when(port.team("team")).thenReturn(team("RECONCILING"));when(port.roster("team")).thenReturn(new Roster("recon","roster","RECONCILING","3",TIME,List.of(member(),member())));service.recover("task");verify(repo).defer(lease,"RECONCILIATION_EVIDENCE_CONFLICT",true);verify(repo,never()).saveRoster(any(),any(),any());}
 @Test void incompleteAndDuplicateSubmissionCannotPassDomainValidation(){assertThrows(IllegalArgumentException.class,()->completion(List.of()).validate(List.of(member())));assertThrows(IllegalArgumentException.class,()->completion(List.of(paid(),paid())).validate(List.of(member())));assertDoesNotThrow(()->completion(List.of(paid())).validate(List.of(member())));}
 @Test void unknownAndMissingRefundIdCannotBeSubmitted(){assertThrows(IllegalArgumentException.class,()->new Decision("user","order","UNKNOWN",null,null,null,null,null,null).validate());assertThrows(IllegalArgumentException.class,()->new Decision("user","order","PAID_OUTSIDE_WINDOW","payment",null,TIME,"9.00","CNY",null).validate());}
 @Test void admissionFailureDoesNotStarveExistingOrUnrelatedRecovery(){doThrow(new IllegalStateException("discovery unavailable")).when(repo).discover(20);when(repo.due(20)).thenReturn(List.of("task","other"));when(repo.claim("task")).thenReturn(lease);when(port.team("team")).thenThrow(new IllegalStateException("offline"));doThrow(new IllegalStateException("retry write offline")).when(repo).defer(any(),anyString(),anyBoolean());service.tick(20,true);verify(repo).claim("other");}
 @Test void recoveryDoesNotRequireNewWorkAdmission(){when(repo.due(20)).thenReturn(List.of("task"));service.tick(20,false);verify(repo,never()).discover(anyInt());verify(repo).claim("task");}
 @Test void responseCannotResolveWrongTeamOrReconciliation(){var c=completion(List.of(paid()));assertThrows(IllegalArgumentException.class,()->new Result("other","recon","FAILED","4",TIME).validate(c));assertThrows(IllegalArgumentException.class,()->new Result("team","other","FAILED","4",TIME).validate(c));}
}
