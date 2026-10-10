package cn.zj.zjmarket.trigger.job;
import cn.zj.zjmarket.domain.payment.service.IPaymentService;
import org.springframework.context.SmartLifecycle;
import java.util.concurrent.*;
public final class PaymentRecoveryJob implements SmartLifecycle {
 private final IPaymentService service;private final boolean enabled;private volatile boolean running;private ScheduledExecutorService executor;
 public PaymentRecoveryJob(IPaymentService service,boolean enabled){this.service=service;this.enabled=enabled;}
 public boolean isAutoStartup(){return enabled;}public boolean isRunning(){return running;}public int getPhase(){return Integer.MAX_VALUE;}
 public synchronized void start(){if(running)return;running=true;executor=Executors.newSingleThreadScheduledExecutor(r->{var t=new Thread(r,"b-payment-recovery");t.setDaemon(true);return t;});executor.scheduleWithFixedDelay(()->{try{if(running)service.tick(20);}catch(Exception e){System.err.println("Payment recovery deferred; durable requests retained ("+e.getClass().getSimpleName()+")");}},0,1000,TimeUnit.MILLISECONDS);}
 public synchronized void stop(){running=false;if(executor!=null){executor.shutdownNow();try{executor.awaitTermination(5,TimeUnit.SECONDS);}catch(InterruptedException e){Thread.currentThread().interrupt();}}}
}
