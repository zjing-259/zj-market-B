package cn.zj.zjmarket.trigger.job;
import cn.zj.zjmarket.domain.reconciliation.service.ReconciliationService;
import org.springframework.context.SmartLifecycle;
import java.util.concurrent.*;
public final class ReconciliationJob implements SmartLifecycle {
 private final ReconciliationService service;private final boolean enabled,discover;private volatile boolean running;private ScheduledExecutorService executor;
 public ReconciliationJob(ReconciliationService service,boolean enabled,boolean discover){this.service=service;this.enabled=enabled;this.discover=discover;}
 public boolean isAutoStartup(){return enabled;}public boolean isRunning(){return running;}public int getPhase(){return Integer.MAX_VALUE-1;}
 public synchronized void start(){if(running)return;running=true;executor=Executors.newSingleThreadScheduledExecutor(r->{var t=new Thread(r,"b-reconciliation");t.setDaemon(true);return t;});executor.scheduleWithFixedDelay(()->{try{service.tick(20,discover);}catch(RuntimeException failure){System.getLogger(ReconciliationJob.class.getName()).log(System.Logger.Level.WARNING,"Reconciliation recovery pending; durable work retained");}},0,2000,TimeUnit.MILLISECONDS);}
 public synchronized void stop(){running=false;if(executor!=null){executor.shutdownNow();try{executor.awaitTermination(5,TimeUnit.SECONDS);}catch(InterruptedException e){Thread.currentThread().interrupt();}}}
}
