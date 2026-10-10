package cn.zj.zjmarket.domain.inventory.service.impl;
import cn.zj.zjmarket.domain.inventory.adapter.repository.IInventoryRepository;
import cn.zj.zjmarket.domain.inventory.model.entity.InventoryAccount;
import cn.zj.zjmarket.domain.inventory.model.valobj.*;
import cn.zj.zjmarket.domain.inventory.service.IInventoryService;
import cn.zj.zjmarket.types.exception.InventoryFailure;
public final class InventoryService implements IInventoryService {
 private final IInventoryRepository repo;public InventoryService(IInventoryRepository repo){this.repo=repo;}
 public InventoryWrite execute(String actor,String operationId,InventoryRequest request) {
  id(actor);id(operationId);
  return repo.transaction(() -> {
   repo.lockOperator(actor);
   var prior=repo.operation(actor,operationId);if(prior!=null)return replay(prior,request);
   if(!repo.lockProduct(request.goodsId()))throw new InventoryFailure(404,"PRODUCT_NOT_FOUND");
   var before=require(request.goodsId(),true);
   prior=repo.operation(actor,operationId);if(prior!=null)return replay(prior,request);
   long now=repo.now();String code="0000";var after=before;
   if(before.version()!=request.expectedVersion())code="INVENTORY_VERSION_CONFLICT";
   else if(before.version()==Long.MAX_VALUE)code="INVENTORY_VERSION_EXHAUSTED";
   else try{after=before.adjust(request.delta(),now);}catch(InventoryFailure e){code=e.code();}catch(ArithmeticException e){code="INVENTORY_QUANTITY_OVERFLOW";}
   var result=new InventoryResult(operationId,request,code.equals("0000")?"SUCCEEDED":"REJECTED",code,code,now,after);
   repo.save(actor,result,before);return new InventoryWrite(result,false);
  });
 }
 private static InventoryWrite replay(InventoryResult prior,InventoryRequest request){
  if(!prior.request().equals(request))throw new InventoryFailure(409,"IDEMPOTENCY_CONFLICT");return new InventoryWrite(prior,true);
 }
 public InventoryResult operation(String actor,String operationId){id(actor);id(operationId);var result=repo.operation(actor,operationId);if(result==null)throw new InventoryFailure(404,"INVENTORY_OPERATION_NOT_FOUND");return result;}
 public InventoryAccount detail(String goodsId){id(goodsId);return require(goodsId,false);}
 public InventoryPage<InventoryAccount> list(int page,int size,String goodsId){page(page,size);if(goodsId!=null)id(goodsId);return repo.transaction(() -> new InventoryPage<>(repo.list(page,size,goodsId),page,size,repo.count(goodsId)));}
 public InventoryPage<InventoryLedger> ledger(String goodsId,int page,int size){id(goodsId);page(page,size);return repo.transaction(() -> {require(goodsId,false);return new InventoryPage<>(repo.ledger(goodsId,page,size),page,size,repo.ledgerCount(goodsId));});}
 private InventoryAccount require(String id,boolean lock){var a=repo.get(id,lock);if(a==null){if(!repo.productExists(id))throw new InventoryFailure(404,"PRODUCT_NOT_FOUND");throw new InventoryFailure(503,"INVENTORY_ACCOUNT_MISSING");}return a;}
 private static void id(String id){if(id==null || !id.matches("[A-Za-z0-9][A-Za-z0-9_-]{0,63}"))throw new InventoryFailure(400,"VALIDATION_FAILED");}
 private static void page(int page,int size){if(page<1 || size<1 || size>100)throw new InventoryFailure(400,"VALIDATION_FAILED");}
}
