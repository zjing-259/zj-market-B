package cn.zj.zjmarket.trigger.job;

import cn.zj.zjmarket.domain.product.adapter.port.IProductResultSubscription;
import cn.zj.zjmarket.domain.product.service.IProductSyncService;
import java.util.concurrent.*;
import org.springframework.context.SmartLifecycle;
/** One bounded background loop; durable leases and fencing also protect concurrent/restarted workers. */
public final class ProductSyncJob implements SmartLifecycle {
 private final IProductSyncService service;private final IProductResultSubscription transport;private final long scanMillis;private final int batchSize;private final boolean schedulerEnabled;private final int retries;private final boolean accelerated;private volatile boolean running;private ScheduledExecutorService executor;
 public ProductSyncJob(IProductSyncService s,IProductResultSubscription t,long scanMillis,int batchSize,boolean schedulerEnabled,int retries,boolean accelerated){service=s;transport=t;this.scanMillis=scanMillis;this.batchSize=batchSize;this.schedulerEnabled=schedulerEnabled;this.retries=retries;this.accelerated=accelerated;}
 public boolean isAutoStartup(){return schedulerEnabled;}public int getPhase(){return Integer.MAX_VALUE;}public boolean isRunning(){return running;}
 public synchronized void start(){if(running)return;running=true;executor=Executors.newSingleThreadScheduledExecutor(r->{var t=new Thread(r,"b-product-sync");t.setDaemon(true);return t;});executor.scheduleWithFixedDelay(this::tick,0,scanMillis,TimeUnit.MILLISECONDS);}
 private void tick(){try{transport.startConsumer(retries,accelerated);for(int i=0;i<batchSize && running;i++){boolean found=i%2==0?service.publishOne(null):service.queryOne(null);if(!found)found=i%2==0?service.queryOne(null):service.publishOne(null);if(!found)break;}}catch(Exception failure){System.err.println("B product sync temporarily unavailable; durable recovery retained ("+failure.getClass().getSimpleName()+")");}}
 public synchronized void stop(){running=false;if(executor!=null){executor.shutdownNow();try{executor.awaitTermination(5,TimeUnit.SECONDS);}catch(InterruptedException e){Thread.currentThread().interrupt();}}}
}
