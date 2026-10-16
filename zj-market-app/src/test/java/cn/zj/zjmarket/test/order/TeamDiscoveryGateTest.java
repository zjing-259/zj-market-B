package cn.zj.zjmarket.test.order;
import cn.zj.zjmarket.trigger.http.TeamDiscoveryGate;
import cn.zj.zjmarket.types.exception.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
class TeamDiscoveryGateTest {
 @Test void perUserWindowAndConcurrentLimit()throws Exception {try(var gate=new TeamDiscoveryGate(2,1)){
  CountDownLatch entered=new CountDownLatch(1),release=new CountDownLatch(1);var t=new Thread(()->gate.run("one",()->{entered.countDown();try{release.await();}catch(InterruptedException e){Thread.currentThread().interrupt();}return 1;}));t.start();assertTrue(entered.await(2,TimeUnit.SECONDS));
  assertEquals("RATE_LIMITED",assertThrows(AuthFailure.class,()->gate.run("two",()->2)).code());release.countDown();t.join(2000);assertFalse(t.isAlive());assertEquals(3,gate.run("one",()->3));assertEquals("RATE_LIMITED",assertThrows(AuthFailure.class,()->gate.run("one",()->4)).code());
 }}
 @Test void totalBudgetEndsSlowRequest() {try(var gate=new TeamDiscoveryGate(30,1)){long start=System.nanoTime();assertEquals("DEPENDENCY_UNAVAILABLE",assertThrows(ProductFailure.class,()->gate.run("one",()->{try{Thread.sleep(15000);}catch(InterruptedException e){Thread.currentThread().interrupt();}return 1;})).code());assertTrue((System.nanoTime()-start)/1_000_000<11000);}}
}
