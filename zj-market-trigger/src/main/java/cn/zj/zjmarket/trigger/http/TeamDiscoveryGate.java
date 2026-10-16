package cn.zj.zjmarket.trigger.http;
import cn.zj.zjmarket.types.exception.AuthFailure;
import cn.zj.zjmarket.types.exception.ProductFailure;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.Supplier;
/** Bounded local admission; worker owns the permit until the remote call really ends. */
public final class TeamDiscoveryGate implements AutoCloseable {
 private record Bucket(long reset,int count) {}
 private final Map<String,Bucket> buckets=new HashMap<>();private final int perMinute;private final Semaphore permits;private final ExecutorService workers;
 public TeamDiscoveryGate(int perMinute,int concurrent){if(perMinute<1||perMinute>600||concurrent<1||concurrent>256)throw new IllegalArgumentException("Invalid discovery limits");this.perMinute=perMinute;permits=new Semaphore(concurrent);workers=new ThreadPoolExecutor(concurrent,concurrent,0,TimeUnit.MILLISECONDS,new SynchronousQueue<>(),r->{Thread t=new Thread(r,"team-discovery-read");t.setDaemon(true);return t;},new ThreadPoolExecutor.AbortPolicy());}
 public <T>T run(String user,Supplier<T> work){take(user);if(!permits.tryAcquire())throw new AuthFailure(429,"RATE_LIMITED",1);Future<T> future;
  try{future=workers.submit(()->{try{return work.get();}finally{permits.release();}});}catch(RejectedExecutionException e){permits.release();throw new AuthFailure(429,"RATE_LIMITED",1);}
  try{return future.get(10,TimeUnit.SECONDS);}catch(TimeoutException e){future.cancel(true);throw new ProductFailure(503,"DEPENDENCY_UNAVAILABLE");}catch(InterruptedException e){future.cancel(true);Thread.currentThread().interrupt();throw new ProductFailure(503,"DEPENDENCY_UNAVAILABLE");}catch(ExecutionException e){if(e.getCause() instanceof RuntimeException x)throw x;throw new ProductFailure(503,"DEPENDENCY_UNAVAILABLE");}
 }
 private synchronized void take(String user){long now=System.currentTimeMillis();buckets.entrySet().removeIf(e->e.getValue().reset<=now);Bucket b=buckets.get(user);if(b!=null&&b.count>=perMinute||b==null&&buckets.size()>=10000)throw new AuthFailure(429,"RATE_LIMITED",b==null?60:Math.max(1,(b.reset-now+999)/1000));buckets.put(user,new Bucket(b==null?now+60000:b.reset,b==null?1:b.count+1));}
 public void close(){workers.shutdownNow();}
}
