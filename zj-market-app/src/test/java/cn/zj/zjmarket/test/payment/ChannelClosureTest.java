package cn.zj.zjmarket.test.payment;
import cn.zj.zjmarket.domain.payment.model.valobj.*;
import org.junit.jupiter.api.Test;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
class ChannelClosureTest {
 private PaymentClose request(){return new PaymentClose("p","c","USER_CANCEL","o","u","s","ch","hash","9.00","CNY",10,100,List.of(new CloseAttempt("a",1,"h1"),new CloseAttempt("b",2,"h2")));}
 private List<ClosedAttempt> all(){return List.of(new ClosedAttempt("a",1,"h1","t1","FAILED"),new ClosedAttempt("b",2,"h2","t2","CLOSED_UNPAID"));}
 @Test void fullFailedAndUncreatedCoverageValid(){assertDoesNotThrow(()->new ChannelClosure(request(),"CLOSED_UNPAID",50L,all(),null).validateUnpaid(request(),60));}
 @Test void truncatedRecentAttemptsNeverProveRoot(){assertThrows(IllegalArgumentException.class,()->new ChannelClosure(request(),"CLOSED_UNPAID",50L,all().subList(1,2),null).validateUnpaid(request(),60));}
 @Test void mismatchedAttemptCannotProveRoot(){var a=new ArrayList<>(all());a.set(1,new ClosedAttempt("other",2,"h2","t2","CLOSED_UNPAID"));assertThrows(IllegalArgumentException.class,()->new ChannelClosure(request(),"CLOSED_UNPAID",50L,a,null).validateUnpaid(request(),60));}
 @Test void openOrSuccessfulAttemptCannotProveUnpaid(){for(String state:List.of("OPEN","SUCCEEDED")){var a=new ArrayList<>(all());a.set(1,new ClosedAttempt("b",2,"h2","t2",state));assertThrows(IllegalArgumentException.class,()->new ChannelClosure(request(),"CLOSED_UNPAID",50L,a,null).validateUnpaid(request(),60));}}
 @Test void futureOrMissingCloseTimeCannotProveUnpaid(){for(Long t:Arrays.asList(null,9L,61L))assertThrows(IllegalArgumentException.class,()->new ChannelClosure(request(),"CLOSED_UNPAID",t,all(),null).validateUnpaid(request(),60));}
}
