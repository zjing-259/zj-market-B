package cn.zj.zjmarket.infrastructure.dao;
import cn.zj.zjmarket.infrastructure.dao.po.*;
import org.apache.ibatis.annotations.*;
import java.util.List;
public interface IInventoryDao {
 String ACCOUNT="goods_id AS goodsId,available,reserved,sold,inventory_version AS version,updated_at_ms AS updatedAt";
 String OP="operation_id AS rowId,operator_id AS actor,operation_key AS operationId,kind,goods_id AS goodsId,delta,expected_version AS expectedVersion,reason,outcome,result_code AS code,completed_at_ms AS completedAt,result_available AS available,result_reserved AS reserved,result_sold AS sold,result_version AS version,result_updated_at_ms AS inventoryUpdatedAt,request_hash AS requestHash";
 @Select("SELECT enabled FROM b_user WHERE user_id=#{id} FOR SHARE") Boolean operatorEnabled(String id);
 @Select("SELECT role FROM b_user_role WHERE user_id=#{id} AND role='OPERATOR' FOR SHARE") String operatorRole(String id);
 @Select("SELECT COUNT(*) FROM b_product WHERE goods_id=#{id}") long productCount(String id);
 @Select("SELECT goods_id FROM b_product WHERE goods_id=#{id} FOR UPDATE") String lockProduct(String id);
 @Select("<script>SELECT "+ACCOUNT+" FROM b_inventory_account WHERE goods_id=#{id}<if test='lock'> FOR UPDATE</if></script>") InventoryRow get(@Param("id")String id,@Param("lock")boolean lock);
 @Select("SELECT "+OP+" FROM b_inventory_operation WHERE operator_id=#{actor} AND operation_key=#{key}") InventoryOperationRow operation(@Param("actor")String actor,@Param("key")String key);
 @Select("SELECT CAST(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3))*1000 AS SIGNED)") long now();
 @Update("UPDATE b_inventory_account SET available=#{available},reserved=#{reserved},sold=#{sold},inventory_version=#{version},updated_at_ms=#{updatedAt} WHERE goods_id=#{goodsId}") int update(InventoryRow row);
 @Insert("INSERT INTO b_inventory_operation(operation_id,operator_id,operation_key,goods_id,kind,delta,expected_version,reason,outcome,result_code,completed_at_ms,result_available,result_reserved,result_sold,result_version,result_updated_at_ms,request_hash) VALUES(#{rowId},#{actor},#{operationId},#{goodsId},#{kind},#{delta},#{expectedVersion},#{reason},#{outcome},#{code},#{completedAt},#{available},#{reserved},#{sold},#{version},#{inventoryUpdatedAt},#{requestHash})") int insertOperation(InventoryOperationRow row);
 @Insert("INSERT INTO b_inventory_ledger(ledger_id,goods_id,operation_id,business_key,kind,delta_available,before_available,after_available,before_reserved,after_reserved,before_sold,after_sold,reason,created_at_ms) VALUES(#{ledgerId},#{goodsId},#{operationId},#{operationId},#{kind},#{delta},#{beforeAvailable},#{afterAvailable},#{reserved},#{reserved},#{sold},#{sold},#{reason},#{createdAt})") int insertLedger(InventoryLedgerRow row);
 @Select("<script>SELECT "+ACCOUNT+" FROM b_inventory_account <where><if test='id != null'>goods_id=#{id}</if></where> ORDER BY goods_id LIMIT #{size} OFFSET #{offset}</script>") List<InventoryRow> list(@Param("id")String id,@Param("offset")long offset,@Param("size")int size);
 @Select("<script>SELECT COUNT(*) FROM b_inventory_account <where><if test='id != null'>goods_id=#{id}</if></where></script>") long count(String id);
 @Select("SELECT l.ledger_id AS ledgerId,l.goods_id AS goodsId,o.operation_key AS operationId,l.kind,l.delta_available AS delta,l.before_available AS beforeAvailable,l.after_available AS afterAvailable,l.after_reserved AS reserved,l.after_sold AS sold,l.reason,l.created_at_ms AS createdAt,o.operator_id AS actorId,l.before_reserved AS beforeReserved,l.before_sold AS beforeSold,l.order_id AS orderId FROM b_inventory_ledger l LEFT JOIN b_inventory_operation o ON o.operation_id=l.operation_id WHERE l.goods_id=#{id} ORDER BY l.created_at_ms DESC,l.ledger_id DESC LIMIT #{size} OFFSET #{offset}") List<InventoryLedgerRow> ledger(@Param("id")String id,@Param("offset")long offset,@Param("size")int size);
 @Select("SELECT COUNT(*) FROM b_inventory_ledger WHERE goods_id=#{id}") long ledgerCount(String id);
}
