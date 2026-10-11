package cn.zj.zjmarket.trigger.job;
import org.springframework.context.SmartLifecycle;
import java.util.concurrent.*;
public final class RefundReleaseJob implements SmartLifecycle {
 private final Runnable action;private final boolean enabled;private volatile boolean running;private ScheduledExecutorService executor;
 public RefundReleaseJob(Runnable action,boolean enabled){this.action=action;this.enabled=enabled;}
 public boolean isAutoStartup(){return enabled;}public boolean isRunning(){return running;}public int getPhase(){return Integer.MAX_VALUE-2;}
 public synchronized void start(){if(running)return;running=true;executor=Executors.newSingleThreadScheduledExecutor(r->{var t=new Thread(r,"b-refund-release");t.setDaemon(true);return t;});executor.scheduleWithFixedDelay(()->{try{action.run();}catch(RuntimeException e){System.getLogger(getClass().getName()).log(System.Logger.Level.WARNING,"Refund inventory recovery retained");}},2000,2000,TimeUnit.MILLISECONDS);}
 public synchronized void stop(){running=false;if(executor!=null){executor.shutdownNow();try{executor.awaitTermination(5,TimeUnit.SECONDS);}catch(InterruptedException e){Thread.currentThread().interrupt();}}}
}
