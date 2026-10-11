package cn.zj.zjmarket.trigger.job;
import cn.zj.zjmarket.domain.refund.service.RefundService;
import cn.zj.zjmarket.domain.refund.model.Refund.Settings;
import org.springframework.context.SmartLifecycle;
import java.util.concurrent.*;
public final class RefundRecoveryJob implements SmartLifecycle {
 private final RefundService service;private final Settings settings;private final boolean enabled,discover;private volatile boolean running;private ScheduledExecutorService executor;
 public RefundRecoveryJob(RefundService service,Settings settings,boolean enabled,boolean discover){this.service=service;this.settings=settings;this.enabled=enabled;this.discover=discover;}
 public boolean isAutoStartup(){return enabled;}public boolean isRunning(){return running;}public int getPhase(){return Integer.MAX_VALUE-1;}
 public synchronized void start(){if(running)return;running=true;executor=Executors.newSingleThreadScheduledExecutor(r->{var t=new Thread(r,"b-refund-recovery");t.setDaemon(true);return t;});executor.scheduleWithFixedDelay(()->{try{service.tick(20,discover);}catch(RuntimeException e){System.getLogger(getClass().getName()).log(System.Logger.Level.WARNING,"Refund recovery pending; durable tasks retained");}},0,settings.scanMillis(),TimeUnit.MILLISECONDS);}
 public synchronized void stop(){running=false;if(executor!=null){executor.shutdownNow();try{executor.awaitTermination(5,TimeUnit.SECONDS);}catch(InterruptedException e){Thread.currentThread().interrupt();}}}
}
