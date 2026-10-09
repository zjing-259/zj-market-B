package cn.zj.zjmarket.verification;

import cn.zj.zjmarket.domain.product.adapter.repository.IProductSyncRepository;
import cn.zj.zjmarket.domain.product.model.valobj.*;
import cn.zj.zjmarket.domain.product.service.IProductService;
import cn.zj.zjmarket.infrastructure.adapter.repository.ProductSyncRepository;
import cn.zj.zjmarket.infrastructure.dao.*;
import java.lang.reflect.*;
import java.sql.Connection;
import java.util.List;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;
import javax.sql.DataSource;
import org.springframework.transaction.support.TransactionTemplate;

/** Real MySQL lock wait; observation only, no fake SQL results or simulated clock. */
final class SyncLeaseRegression {
    static void verify(IProductService products,IProductSyncRepository store,DataSource db,List<String> evidence)throws Exception {
        var product=products.create(SyncCommands.fields("租约跨真实行锁等待",SaleStatus.OFF_SALE),"lease-lock-wait");
        String id=product.sync().targetEventId();var claimed=store.claim("SEND",id,30000);
        SyncCommands.check(claimed!=null,"lock-wait fixture claimed");
        // Reuse the real application's mapper/session and transaction configuration.
        var mapper=(IProductSyncDao)field(store,"m");
        var rowLockAttempt=new CountDownLatch(1);var observedNow=new AtomicLong(-1);
        var observed=(IProductSyncDao)Proxy.newProxyInstance(IProductSyncDao.class.getClassLoader(),new Class[]{IProductSyncDao.class},(proxy,method,args)->{
            if(method.getName().equals("sent") || (method.getName().equals("event") && Boolean.TRUE.equals(args[1])))rowLockAttempt.countDown();
            try {var result=method.invoke(mapper,args);if(method.getName().equals("now"))observedNow.set((Long)result);return result;}
            catch(InvocationTargetException e){throw e.getCause();}
        });
        var repository=new ProductSyncRepository(observed,(IProductDao)field(store,"products"),(TransactionTemplate)field(store,"tx"));
        var executor=Executors.newSingleThreadExecutor();
        try {
            // Set a short real lease before the blocking transaction takes its row lock.
            SyncCommands.sql(db,"UPDATE b_product_outbox SET lease_until_ms=CAST(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3))*1000 AS SIGNED)+2500 WHERE event_id=?",id);
            long deadline;
            try(var holder=db.getConnection()) {
                holder.setAutoCommit(false);
                try(var statement=holder.prepareStatement("SELECT lease_until_ms FROM b_product_outbox WHERE event_id=? FOR UPDATE")) {
                    statement.setString(1,id);try(var rows=statement.executeQuery()){SyncCommands.check(rows.next(),"lock-wait fixture exists");deadline=rows.getLong(1);}
                }
                SyncCommands.check(now(holder)<deadline,"lease active before row-lock wait");
                Future<?> writer=executor.submit(()->repository.sent(claimed,2000));
                SyncCommands.check(rowLockAttempt.await(5,TimeUnit.SECONDS),"sender reached real locking SQL");
                SyncCommands.check(now(holder)<deadline,"sender entered before lease deadline");
                try {writer.get(150,TimeUnit.MILLISECONDS);throw new IllegalStateException("check: sender did not wait on real MySQL row lock");}
                catch(TimeoutException expected) { /* Holder owns the exact outbox row. */ }
                long limit=System.nanoTime()+TimeUnit.SECONDS.toNanos(8);
                while(now(holder)<=deadline+100) {
                    if(System.nanoTime()>limit)throw new IllegalStateException("check: bounded lease expiry wait exceeded");
                    Thread.sleep(25);
                }
                holder.commit(); // Release only after the database lease is actually expired.
                writer.get(10,TimeUnit.SECONDS);
            }
            var after=store.event(id);
            SyncCommands.check(observedNow.get()>deadline,"writeback reads database time after expired row-lock wait");
            SyncCommands.check(after.deliveryState().equals("PENDING") && claimed.leaseToken().equals(after.leaseToken()),"expired sender cannot mark published or clear token");
            var fresh=store.claim("SEND",id,30000);
            SyncCommands.check(fresh!=null && !fresh.leaseToken().equals(claimed.leaseToken()),"new sender reclaims expired lease");
            store.sent(claimed,2000);
            SyncCommands.check(store.event(id).deliveryState().equals("PENDING"),"old lease token cannot acknowledge reclaimed event");
            store.sent(fresh,2000);
            SyncCommands.check(store.event(id).deliveryState().equals("PUBLISHED"),"active replacement lease can acknowledge");
            evidence.add("actual-MySQL/two-connections/outbox-row-lock-wait-crosses-lease-expiry/lock-before-database-time/stale-token-denied/new-lease-ack=PASSED");
        } finally {
            executor.shutdownNow();SyncCommands.check(executor.awaitTermination(10,TimeUnit.SECONDS),"lock-wait verification worker released");
        }
    }
    private static Object field(Object instance,String name)throws Exception {
        var field=ProductSyncRepository.class.getDeclaredField(name);field.setAccessible(true);return field.get(instance);
    }
    private static long now(Connection connection)throws Exception {
        try(var statement=connection.createStatement();var row=statement.executeQuery("SELECT CAST(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3))*1000 AS SIGNED)")){row.next();return row.getLong(1);}
    }
}
