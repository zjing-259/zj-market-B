package cn.zj.zjmarket.trigger.job;
import cn.zj.zjmarket.domain.order.service.ITradeCoordinationService;
import org.springframework.context.SmartLifecycle;
import java.util.concurrent.*;
public final class TradeRecoveryJob implements SmartLifecycle {
 private final ITradeCoordinationService service;private final long scan;private final int batch;private final boolean enabled;private volatile boolean running;private ScheduledExecutorService executor;
 public TradeRecoveryJob(ITradeCoordinationService service,long scan,int batch,boolean enabled){this.service=service;this.scan=scan;this.batch=batch;this.enabled=enabled;}
 public boolean isAutoStartup(){return enabled;}public boolean isRunning(){return running;}public int getPhase(){return Integer.MAX_VALUE;}
 public synchronized void start(){if(running)return;running=true;executor=Executors.newSingleThreadScheduledExecutor(r->{var t=new Thread(r,"b-trade-recovery");t.setDaemon(true);return t;});executor.scheduleWithFixedDelay(()->{try{if(running)service.tick(batch);}catch(Exception e){System.err.println("B trade recovery temporarily unavailable; original durable requests retained ("+e.getClass().getSimpleName()+")");}},0,scan,TimeUnit.MILLISECONDS);}
 public synchronized void stop(){running=false;if(executor!=null){executor.shutdownNow();try{executor.awaitTermination(5,TimeUnit.SECONDS);}catch(InterruptedException e){Thread.currentThread().interrupt();}}}
}
