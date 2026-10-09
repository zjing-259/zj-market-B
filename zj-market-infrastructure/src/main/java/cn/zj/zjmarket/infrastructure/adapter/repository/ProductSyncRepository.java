package cn.zj.zjmarket.infrastructure.adapter.repository;

import cn.zj.zjmarket.domain.product.adapter.repository.IProductSyncRepository;
import cn.zj.zjmarket.domain.product.model.valobj.ProductSyncProgress;
import cn.zj.zjmarket.domain.product.model.valobj.QuarantinePage;
import cn.zj.zjmarket.domain.product.model.valobj.SyncBadMessage;
import cn.zj.zjmarket.domain.product.model.valobj.SyncResult;
import cn.zj.zjmarket.domain.product.model.valobj.SyncWork;
import cn.zj.zjmarket.infrastructure.dao.IProductDao;
import cn.zj.zjmarket.infrastructure.dao.IProductSyncDao;
import cn.zj.zjmarket.infrastructure.gateway.codec.ContractCodec;
import cn.zj.zjmarket.types.exception.ProductFailure;
import cn.zj.zjmarket.types.exception.SyncTransportFailure;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;
import org.springframework.transaction.support.TransactionTemplate;
/** All business-result changes lock product -> outbox -> inbox/sync, matching product edits. */
public final class ProductSyncRepository implements IProductSyncRepository {
 private final IProductSyncDao m;private final IProductDao products;private final TransactionTemplate tx;
 public ProductSyncRepository(IProductSyncDao m,IProductDao products,TransactionTemplate tx){this.m=m;this.products=products;this.tx=tx;}
 public SyncWork event(String id){return m.event(id,false);}
 public SyncWork claim(String kind,String id,long leaseMillis){return tx.execute(status -> {
  var w=m.candidate(kind,id);if(w==null)return null;
  // Database time is read after locking the candidate, not before any lock wait.
  long now=m.now();String token=UUID.randomUUID().toString();m.claim(w.eventId(),token,now+leaseMillis,kind.equals("SEND")?1:0,kind.equals("QUERY")?1:0);return m.event(w.eventId(),false);
 });}
 public void sent(SyncWork w,long queryMillis){tx.executeWithoutResult(status -> {long now=m.now();m.sent(w.eventId(),w.leaseToken(),now,now+queryMillis);});}
 public void failed(SyncWork w,String kind,String code,boolean permanent,long delay){tx.executeWithoutResult(status -> {
  var locked=lock(w.eventId());if(locked==null)return;long now=m.now();String error=!permanent && kind.equals("SEND") && w.sendFailures()+1>=5?"PUBLISH_FAILED_ALERT":code;
  if(m.failed(w.eventId(),w.leaseToken(),now,kind.equals("SEND")?1:0,error,permanent?"RECONCILIATION_REQUIRED":"WAITING",permanent,now+delay,now+delay)==1)
   m.progress(w.goodsId(),w.eventId(),w.version(),permanent?"RECONCILIATION_REQUIRED":"PENDING",error,time(now));
 });}
 public void checked(SyncWork w,String state,long queryMillis){tx.executeWithoutResult(status -> {var locked=lock(w.eventId());if(locked==null)return;long now=m.now();if(m.checked(w.eventId(),w.leaseToken(),now,now+queryMillis,state)==1)m.progress(w.goodsId(),w.eventId(),w.version(),"PENDING",state,time(now));});}
 public void accept(SyncResult r,String consumer){String invalid=tx.execute(status -> {
  var w=lock(r.originalEventId());if(w==null)return "UNKNOWN_ORIGINAL_EVENT";
  var prior=m.inbox(consumer,r.producer(),r.receiptId());
  if(prior!=null){if(prior.bodyHash().equals(r.receiptHash()))return null;return "INBOX_BODY_CONFLICT";}
  m.inboxInsert(consumer,r.producer(),r.receiptId(),r.receiptHash(),r.originalEventId(),r.outcome(),resultBody(r),m.now());
  String oldHash=m.resultHash(w.eventId());
  if(oldHash!=null && !oldHash.equals(r.factHash())){
   m.result(w.eventId(),"RECONCILIATION_REQUIRED",oldHash,r.outcome(),r.code(),"RESULT_CONFLICT",resultBody(r));m.progress(w.goodsId(),w.eventId(),w.version(),"RECONCILIATION_REQUIRED","RESULT_CONFLICT",time(m.now()));return "RESULT_CONFLICT";
  }
  // Conflicting evidence is sticky: a later repeat of the first fact cannot erase the conflict.
  if(w.processingState().equals("RECONCILIATION_REQUIRED") && "RESULT_CONFLICT".equals(m.eventError(w.eventId())))return null;
  boolean rejected=r.outcome().equals("REJECTED");boolean confirmed=!rejected && w.goodsId().equals(r.goodsId()) && Long.toString(w.version()).equals(r.currentVersion()) && w.saleStatus().equals(r.saleStatus());
  String state=rejected?"REJECTED":confirmed?"CONFIRMED":"RECONCILIATION_REQUIRED";String error=rejected?r.code():confirmed?null:"RESULT_VERSION_MISMATCH";
  m.result(w.eventId(),state,r.factHash(),r.outcome(),r.code(),error,resultBody(r));
  if(confirmed)m.confirmed(w.goodsId(),w.version());
  m.progress(w.goodsId(),w.eventId(),w.version(),state,error,time(m.now()));return null;
 });if(invalid!=null)throw new SyncTransportFailure(invalid,true);}
 public ProductSyncProgress progress(String id){return tx.execute(status -> {if(products.get(id,false)==null)throw new ProductFailure(404,"PRODUCT_NOT_FOUND");return products.progress(id);});}
 public void control(String id,String eventId,long expected,String operator,boolean pause){tx.executeWithoutResult(status -> {
  var p=products.get(id,true);if(p==null)throw new ProductFailure(404,"PRODUCT_NOT_FOUND");var target=products.progress(id);var w=m.event(eventId,true);
  if(w==null || p.version()!=expected || w.version()!=expected || !w.goodsId().equals(id) || !target.targetEventId().equals(eventId))throw new ProductFailure(409,"RETRY_NOT_ALLOWED");
  if(!w.processingState().equals("WAITING") && !(w.processingState().equals("RECONCILIATION_REQUIRED") && !Set.of("RESULT_VERSION_MISMATCH","RESULT_CONFLICT","INBOX_BODY_CONFLICT","LOCAL_FACT_INVALID").contains(target.lastError()==null?"":target.lastError())))throw new ProductFailure(409,"RETRY_NOT_ALLOWED");
  long now=m.now();m.control(eventId,pause,pause?"MANUALLY_PAUSED":null,now);m.progress(id,eventId,expected,pause?"RECONCILIATION_REQUIRED":"PENDING",pause?"MANUALLY_PAUSED":null,time(now));m.audit(UUID.randomUUID().toString(),id,eventId,operator,pause?"PAUSE":"RETRY",now);
 });}
 private SyncWork lock(String id){var known=m.event(id,false);if(known==null)return null;products.get(known.goodsId(),true);return m.event(id,true);}
 public String quarantine(SyncBadMessage bad){return tx.execute(status -> {
  try{byte[] body=bad.body()==null?new byte[0]:bad.body();String hash=ContractCodec.sha256(body);String reason=shorten(bad.reason(),64),topic=shorten(bad.topic(),255),tag=shorten(bad.tag(),128),key=shorten(bad.keyId(),128),signature=shorten(bad.signature(),256);
   String dedup=ContractCodec.sha256(String.join("\n",Objects.toString(topic,""),Objects.toString(tag,""),Objects.toString(key,""),Objects.toString(signature,""),hash,reason).getBytes(java.nio.charset.StandardCharsets.UTF_8));
   m.quarantine(UUID.randomUUID().toString(),dedup,hash,topic,tag,key,signature,Arrays.copyOf(body,Math.min(body.length,256*1024)),body.length,reason,m.now());return m.quarantineId(dedup);
  }catch(java.security.GeneralSecurityException e){throw new IllegalStateException("Hash unavailable");}catch(Exception e){if(e instanceof RuntimeException runtime)throw runtime;throw new IllegalStateException("Quarantine unavailable");}
 });}
 public QuarantinePage quarantined(int page,int size){return tx.execute(status -> new QuarantinePage(m.quarantined(size,((long)page-1)*size),page,size,m.quarantineCount()));}
 public SyncBadMessage quarantinedBody(String id){var bad=m.quarantinedBody(id);if(bad==null)throw new ProductFailure(409,"RETRY_NOT_ALLOWED");return bad;}
 public void replayed(String id){m.replayed(id,m.now());}
 private static String resultBody(SyncResult r){try{return new String(new ContractCodec().encode(r),java.nio.charset.StandardCharsets.UTF_8);}catch(Exception e){throw new IllegalStateException("Result serialization unavailable");}}
 private static String shorten(String value,int max){return value==null?null:value.substring(0,Math.min(max,value.length()));}
 private static String time(long now){return DateTimeFormatter.ofPattern("uuuu-MM-dd'T'HH:mm:ss.SSS'Z'").withZone(ZoneOffset.UTC).format(Instant.ofEpochMilli(now));}
}
