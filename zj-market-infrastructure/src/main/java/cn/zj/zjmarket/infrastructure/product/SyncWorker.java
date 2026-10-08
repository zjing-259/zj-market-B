package cn.zj.zjmarket.infrastructure.product;
import cn.zj.zjmarket.application.product.ProductSyncService;
import org.springframework.context.SmartLifecycle;
import java.util.concurrent.*;
/** One bounded background loop; durable leases and fencing also protect concurrent/restarted workers. */
public final class SyncWorker implements SmartLifecycle {
 private final ProductSyncService service;private final RocketMqSyncTransport transport;private final SyncSettings settings;private volatile boolean running;private ScheduledExecutorService executor;
 public SyncWorker(ProductSyncService s,RocketMqSyncTransport t,SyncSettings c){service=s;transport=t;settings=c;}
 public boolean isAutoStartup(){return settings.isSchedulerEnabled();}public int getPhase(){return Integer.MAX_VALUE;}public boolean isRunning(){return running;}
 public synchronized void start(){if(running)return;running=true;executor=Executors.newSingleThreadScheduledExecutor(r->{var t=new Thread(r,"b-product-sync");t.setDaemon(true);return t;});executor.scheduleWithFixedDelay(this::tick,0,settings.getScanMillis(),TimeUnit.MILLISECONDS);}
 private void tick(){try{transport.startConsumer(settings.getMaxReconsumeTimes(),settings.isAcceleratedTest());for(int i=0;i<settings.getBatchSize() && running;i++){boolean found=i%2==0?service.publishOne(null):service.queryOne(null);if(!found)found=i%2==0?service.queryOne(null):service.publishOne(null);if(!found)break;}}catch(Exception failure){System.err.println("B product sync temporarily unavailable; durable recovery retained ("+failure.getClass().getSimpleName()+")");}}
 public synchronized void stop(){running=false;if(executor!=null){executor.shutdownNow();try{executor.awaitTermination(5,TimeUnit.SECONDS);}catch(InterruptedException e){Thread.currentThread().interrupt();}}}
}
