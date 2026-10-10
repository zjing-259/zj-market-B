package cn.zj.zjmarket.infrastructure.adapter.repository;
import cn.zj.zjmarket.domain.inventory.adapter.repository.IInventoryRepository;
import cn.zj.zjmarket.domain.inventory.model.entity.InventoryAccount;
import cn.zj.zjmarket.domain.inventory.model.valobj.*;
import cn.zj.zjmarket.infrastructure.dao.IInventoryDao;
import cn.zj.zjmarket.infrastructure.dao.po.*;
import cn.zj.zjmarket.types.exception.AuthFailure;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.dao.DuplicateKeyException;
import java.util.*;
import java.util.function.Supplier;
public final class InventoryRepository implements IInventoryRepository {
 private final IInventoryDao dao;private final TransactionTemplate tx;
 public InventoryRepository(IInventoryDao dao,TransactionTemplate tx){this.dao=dao;this.tx=tx;}
 public <T>T transaction(Supplier<T> work){
  // Roll back a cross-SKU same-key unique race, then compare the committed winner.
  try{return tx.execute(s -> work.get());}catch(DuplicateKeyException race){return tx.execute(s -> work.get());}
 }
 public void lockOperator(String actor){if(!Boolean.TRUE.equals(dao.operatorEnabled(actor)) || dao.operatorRole(actor)==null)throw new AuthFailure(403,"FORBIDDEN");}
 public boolean productExists(String id){return dao.productCount(id)==1;}
 public boolean lockProduct(String id){return dao.lockProduct(id)!=null;}
 public InventoryAccount get(String id,boolean lock){var r=dao.get(id,lock);return r==null?null:account(r);}
 public InventoryResult operation(String actor,String key){var r=dao.operation(actor,key);if(r!=null && !r.requestHash().equals(hash(actor,new InventoryRequest(r.kind(),r.goodsId(),r.delta(),r.expectedVersion(),r.reason()))))throw new IllegalStateException("Inventory audit mismatch");return r==null?null:new InventoryResult(r.operationId(),new InventoryRequest(r.kind(),r.goodsId(),r.delta(),r.expectedVersion(),r.reason()),r.outcome(),r.code(),r.code(),r.completedAt(),new InventoryAccount(r.goodsId(),r.available(),r.reserved(),r.sold(),r.version(),r.inventoryUpdatedAt()));}
 public long now(){return dao.now();}
 public void save(String actor,InventoryResult result,InventoryAccount before){
  var q=result.request();var a=result.inventory();String id=UUID.randomUUID().toString();
  one(dao.insertOperation(new InventoryOperationRow(id,actor,result.operationId(),q.kind(),q.goodsId(),q.delta(),q.expectedVersion(),q.reason(),result.outcome(),result.code(),result.completedAt(),a.available(),a.reserved(),a.sold(),a.version(),a.updatedAt(),hash(actor,q))));
  if(result.outcome().equals("SUCCEEDED")){
   one(dao.update(new InventoryRow(a.goodsId(),a.available(),a.reserved(),a.sold(),a.version(),a.updatedAt())));
   one(dao.insertLedger(new InventoryLedgerRow(UUID.randomUUID().toString(),a.goodsId(),id,q.kind(),q.delta(),before.available(),a.available(),a.reserved(),a.sold(),q.reason(),result.completedAt(),actor,a.reserved(),a.sold(),null)));
  }
 }
 public List<InventoryAccount> list(int page,int size,String id){return dao.list(id,((long)page-1)*size,size).stream().map(InventoryRepository::account).toList();}
 public long count(String id){return dao.count(id);}
 public List<InventoryLedger> ledger(String id,int page,int size){return dao.ledger(id,((long)page-1)*size,size).stream().map(r -> new InventoryLedger(r.ledgerId(),r.goodsId(),r.operationId(),r.kind(),r.delta(),r.beforeAvailable(),r.afterAvailable(),r.reserved(),r.sold(),r.reason(),r.createdAt(),r.actorId(),r.beforeReserved(),r.beforeSold(),r.orderId())).toList();}
 public long ledgerCount(String id){return dao.ledgerCount(id);}
 private static InventoryAccount account(InventoryRow r){return new InventoryAccount(r.goodsId(),r.available(),r.reserved(),r.sold(),r.version(),r.updatedAt());}
 private static String hash(String actor,InventoryRequest q){
  String canonical=String.join("\n",actor,q.kind(),q.goodsId(),Long.toString(q.delta()),Long.toString(q.expectedVersion()),q.reason());
  try{return java.util.HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(canonical.getBytes(java.nio.charset.StandardCharsets.UTF_8)));}catch(java.security.NoSuchAlgorithmException impossible){throw new IllegalStateException(impossible);}
 }
 private static void one(int n){if(n!=1)throw new IllegalStateException("Inventory write mismatch");}
}
