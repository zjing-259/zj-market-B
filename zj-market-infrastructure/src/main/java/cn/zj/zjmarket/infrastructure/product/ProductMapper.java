package cn.zj.zjmarket.infrastructure.product;
import org.apache.ibatis.annotations.*;
import java.math.BigDecimal;
import java.util.List;
public interface ProductMapper {
    String COLUMNS="goods_id AS goodsId,goods_name AS goodsName,description,image_url AS imageUrl,original_price AS originalPrice,currency,sale_status AS saleStatus,product_version AS version,created_at_ms AS createdAt,updated_at_ms AS updatedAt";
    record Row(String goodsId,String goodsName,String description,String imageUrl,BigDecimal originalPrice,String currency,String saleStatus,long version,long createdAt,long updatedAt){}
    @Select("<script>SELECT "+COLUMNS+" FROM b_product WHERE goods_id=#{id}<if test='lock'> FOR UPDATE</if></script>") Row get(@Param("id")String id,@Param("lock")boolean lock);
    @Select("SELECT goods_id AS goodsId,CAST(target_version AS CHAR) AS targetVersion,target_event_id AS targetEventId,CAST(confirmed_version AS CHAR) AS confirmedVersion,state,last_error AS lastError,checked_at AS checkedAt FROM b_product_sync WHERE goods_id=#{id}")
    cn.zj.zjmarket.domain.product.ProductSyncProgress progress(String id);
    @Insert("INSERT INTO b_product(goods_id,goods_name,description,image_url,original_price,currency,sale_status,product_version,created_at_ms,updated_at_ms) VALUES(#{goodsId},#{goodsName},#{description},#{imageUrl},#{originalPrice},#{currency},#{saleStatus},#{version},#{createdAt},#{updatedAt})") int insert(Row row);
    @Update("UPDATE b_product SET goods_name=#{p.goodsName},description=#{p.description},image_url=#{p.imageUrl},original_price=#{p.originalPrice},currency=#{p.currency},sale_status=#{p.saleStatus},product_version=#{p.version},updated_at_ms=#{p.updatedAt} WHERE goods_id=#{p.goodsId} AND product_version=#{expected}") int update(@Param("p")Row row,@Param("expected")long expected);
    @Insert("INSERT INTO b_product_outbox(event_id,goods_id,product_version,event_type,body,delivery_state,created_at_ms,body_hash,snapshot_sale_status) VALUES(#{eventId},#{id},#{version},'PRODUCT_SNAPSHOT_CHANGED',#{body},'PENDING',#{now},SHA2(#{body},256),JSON_UNQUOTE(JSON_EXTRACT(#{body},'$.payload.saleStatus')))") int append(@Param("id")String id,@Param("version")long version,@Param("eventId")String eventId,@Param("body")String body,@Param("now")long now);
    @Insert("INSERT INTO b_product_sync(goods_id,target_version,target_event_id,state) VALUES(#{id},#{version},#{eventId},'PENDING') ON DUPLICATE KEY UPDATE target_version=#{version},target_event_id=#{eventId},state='PENDING',last_error=NULL,checked_at=NULL") int target(@Param("id")String id,@Param("version")long version,@Param("eventId")String eventId);
    @Select("<script>SELECT "+COLUMNS+" FROM b_product <where><if test='status != null'>sale_status=#{status}</if></where> ORDER BY created_at_ms DESC,goods_id DESC LIMIT #{size} OFFSET #{offset}</script>") List<Row> list(@Param("offset")long offset,@Param("size")int size,@Param("status")String status);
    @Select("<script>SELECT COUNT(*) FROM b_product <where><if test='status != null'>sale_status=#{status}</if></where></script>") long count(@Param("status")String status);
}
