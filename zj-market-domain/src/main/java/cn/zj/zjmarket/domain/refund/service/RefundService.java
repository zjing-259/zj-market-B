package cn.zj.zjmarket.domain.refund.service;
import cn.zj.zjmarket.domain.refund.adapter.repository.IRefundRepository;
import cn.zj.zjmarket.domain.refund.adapter.port.IRefundChannel;
import cn.zj.zjmarket.domain.refund.model.Refund.*;
import java.util.concurrent.*;
import java.util.function.Supplier;

/** Network calls never run within a marketplace transaction. Fenced writes survive lost responses. */
public final class RefundService implements AutoCloseable {
 private final IRefundRepository repo;private final IRefundChannel channel;private final Settings settings;
 private final ExecutorService calls=Executors.newVirtualThreadPerTaskExecutor();
 private final ScheduledExecutorService renewals=Executors.newScheduledThreadPool(2,r->{var t=new Thread(r,"b-refund-renew");t.setDaemon(true);return t;});
 public RefundService(IRefundRepository repo,IRefundChannel channel,Settings settings){this.repo=repo;this.channel=channel;this.settings=settings;}
 private <T>T call(Supplier<T> action){Future<T> f=calls.submit(action::get);try{return f.get(settings.timeoutMillis(),TimeUnit.MILLISECONDS);}catch(ExecutionException e){if(e.getCause() instanceof IllegalArgumentException c)throw c;throw new IllegalStateException("Refund channel pending",e.getCause());}catch(InterruptedException e){Thread.currentThread().interrupt();throw new IllegalStateException("Refund recovery interrupted",e);}catch(TimeoutException e){throw new IllegalStateException("Refund channel pending",e);}finally{if(!f.isDone())f.cancel(true);}}
 public void tick(int size,boolean discover){if(discover)try{repo.discover(size);}catch(RuntimeException e){System.getLogger(getClass().getName()).log(System.Logger.Level.WARNING,"Refund discovery pending");}for(String id:repo.due(size))try{recover(id);}catch(RuntimeException e){System.getLogger(getClass().getName()).log(System.Logger.Level.WARNING,"Refund task retained");}notices(size);}
 public void recover(String id){Lease lease=repo.claim(id);if(lease==null)return;var valid=new java.util.concurrent.atomic.AtomicBoolean(true);var renewal=renewals.scheduleWithFixedDelay(()->{try{if(!repo.renew(lease))valid.set(false);}catch(RuntimeException ignored){valid.set(false);}},settings.renewMillis(),settings.renewMillis(),TimeUnit.MILLISECONDS);try{Fact fact=call(()->channel.query(lease.request()));if(lease.checkOnly()){if(valid.get())repo.finishCheck(lease,fact);return;}if(fact==null){if(!valid.get()||!repo.authorize(lease))return;fact=call(()->channel.execute(lease.request()));}if(valid.get())repo.finish(lease,fact);}catch(IllegalArgumentException conflict){if(valid.get())repo.defer(lease,true);}catch(RuntimeException unknown){if(valid.get()){if(lease.checkOnly())repo.finishCheck(lease,null);else repo.defer(lease,false);}}finally{renewal.cancel(false);}}
 public void notices(int size){for(Notice notice:channel.notices(size)){var valid=new java.util.concurrent.atomic.AtomicBoolean(true);var renewal=renewals.scheduleWithFixedDelay(()->{try{if(!channel.renew(notice))valid.set(false);}catch(RuntimeException ignored){valid.set(false);}},settings.renewMillis(),settings.renewMillis(),TimeUnit.MILLISECONDS);try{recover(notice.refundId());/* Notice only wakes the original task. The stored result is always from an independent query. */
  // The channel query requires the immutable marketplace request, not untrusted notification payload.
  var request=repo.noticeRequest(notice);var fact=request==null?null:call(()->channel.query(request));if(valid.get()){if(repo.applied(fact))channel.acknowledge(notice,false);else channel.retry(notice);}
 }catch(IllegalArgumentException conflict){if(valid.get()){repo.quarantineNotice(notice);channel.acknowledge(notice,true);}}catch(RuntimeException failure){if(valid.get())channel.retry(notice);}finally{renewal.cancel(false);}}}
 public void close(){renewals.shutdownNow();calls.shutdownNow();}
}
