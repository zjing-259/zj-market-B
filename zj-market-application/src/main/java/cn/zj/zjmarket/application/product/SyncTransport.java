package cn.zj.zjmarket.application.product;
/** SDK-free integration port. Raw immutable fact bytes are never rebuilt for retries. */
public interface SyncTransport {
    void publish(SyncStore.Work work);
    Query query(SyncStore.Work work);
    record Result(String receiptId,String producer,String receiptHash,String originalEventId,String outcome,String code,String processedAt,String goodsId,String currentVersion,Boolean applied,String saleStatus,String factHash){}
    record Query(String status,Result result){}
    final class Failure extends RuntimeException {
        private final String code;private final boolean permanent;
        public Failure(String code,boolean permanent){super(code);this.code=code;this.permanent=permanent;}
        public String code(){return code;}public boolean permanent(){return permanent;}
    }
}
