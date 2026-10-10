package cn.zj.zjmarket.trigger.job;
import cn.zj.zjmarket.domain.payment.service.ISettlementService;
import cn.zj.zjmarket.domain.payment.adapter.port.ISettlementTransport;
import org.springframework.context.SmartLifecycle;
import java.util.concurrent.*;
public final class SettlementJob implements SmartLifecycle {
 private cn.zj.zjmarket.domain.payment.service.impl.FulfillmentService fulfillment;
 public void enableFulfillment(cn.zj.zjmarket.domain.payment.service.impl.FulfillmentService service){fulfillment=service;}
 private final ISettlementService service;private final ISettlementTransport transport;private final boolean enabled;private volatile boolean running;private ScheduledExecutorService executor;
 public SettlementJob(ISettlementService service,ISettlementTransport transport,boolean enabled){this.service=service;this.transport=transport;this.enabled=enabled;}
 public boolean isAutoStartup(){return enabled;}public boolean isRunning(){return running;}public int getPhase(){return Integer.MAX_VALUE;}
 public synchronized void start(){if(running)return;running=true;executor=Executors.newSingleThreadScheduledExecutor(r->{var t=new Thread(r,"b-trade-facts");t.setDaemon(true);return t;});executor.scheduleWithFixedDelay(()->{try{transport.start();}catch(Exception e){System.err.println("Trade subscriptions pending; durable recovery retained");}try{service.tick(20);}catch(RuntimeException e){System.err.println("Trade facts pending; durable recovery retained");}try{if(fulfillment!=null)fulfillment.tick(20);}catch(RuntimeException e){System.err.println("Fulfillment pending; durable recovery retained");}},0,2000,TimeUnit.MILLISECONDS);}
 public synchronized void stop(){running=false;if(executor!=null){executor.shutdownNow();try{executor.awaitTermination(5,TimeUnit.SECONDS);}catch(InterruptedException e){Thread.currentThread().interrupt();}}}
}
