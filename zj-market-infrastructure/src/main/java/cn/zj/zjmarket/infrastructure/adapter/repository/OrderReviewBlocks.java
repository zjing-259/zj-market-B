package cn.zj.zjmarket.infrastructure.adapter.repository;
import org.springframework.jdbc.core.JdbcTemplate;
import java.util.*;

/** Used only after explicit V14 capability validation; all writes hold the order prefix. */
public final class OrderReviewBlocks {
 private final JdbcTemplate db;
 public OrderReviewBlocks(JdbcTemplate db){this.db=db;}
 private long count(String q,Object...a){return db.queryForObject(q,Long.class,a);}
 public boolean canRecover(String id){
  return count("SELECT COUNT(*) FROM b_order_block WHERE order_id=? AND kind='RECONCILIATION' AND state='ACTIVE'",id)>0
   &&count("SELECT COUNT(*) FROM b_order_block WHERE order_id=? AND kind<>'RECONCILIATION' AND state='ACTIVE'",id)==0
   &&count("SELECT COUNT(*) FROM b_market_order o LEFT JOIN b_payment p ON p.order_id=o.order_id WHERE o.order_id=? AND (o.review_required AND COALESCE(o.last_error,'') NOT IN ('TEAM_RECONCILIATION_REQUIRED','TEAM_FAILED','PAYMENT_OUTSIDE_WINDOW') OR p.review_required AND COALESCE(p.last_error,'') NOT IN ('TEAM_RECONCILIATION_REQUIRED','TEAM_FAILED','PAYMENT_OUTSIDE_WINDOW'))",id)==0;
 }
 public void capture(String id,String team,long version,String reason,long now){
  // Never infer that an old unowned true flag was only a normal reconciliation block.
  if(count("SELECT COUNT(*) FROM b_order_block WHERE order_id=?",id)==0&&count("SELECT COUNT(*) FROM b_market_order o LEFT JOIN b_payment p ON p.order_id=o.order_id WHERE o.order_id=? AND (o.review_required OR p.review_required)",id)>0)
   add(id,"LEGACY_REVIEW",id,1,"UNCLASSIFIED_EXISTING_REVIEW",now);
  add(id,"RECONCILIATION",team,version,reason,now);
 }
 private void add(String id,String kind,String owner,long version,String reason,long now){db.update("INSERT INTO b_order_block(order_id,kind,owner_id,owner_version,reason,created_at_ms,updated_at_ms) VALUES(?,?,?,?,?,?,?) ON DUPLICATE KEY UPDATE owner_version=GREATEST(owner_version,VALUES(owner_version)),updated_at_ms=VALUES(updated_at_ms)",id,kind,owner,version,reason,now,now);}
 public void clear(String id,String team,long version,long now){
  db.update("UPDATE b_order_block SET state='CLEARED',updated_at_ms=? WHERE order_id=? AND kind='RECONCILIATION' AND owner_id=? AND owner_version<=?",now,id,team,version);
  if(count("SELECT COUNT(*) FROM b_order_block WHERE order_id=? AND state='ACTIVE'",id)==0){
   db.update("UPDATE b_market_order SET review_required=FALSE,last_error=NULL,order_version=order_version+1,updated_at_ms=? WHERE order_id=? AND review_required=TRUE AND last_error IN ('TEAM_RECONCILIATION_REQUIRED','TEAM_FAILED')",now,id);
   db.update("UPDATE b_payment SET review_required=FALSE,last_error=NULL,version=version+1,updated_at_ms=? WHERE order_id=? AND review_required=TRUE AND last_error IN ('TEAM_RECONCILIATION_REQUIRED','TEAM_FAILED')",now,id);
  }
 }
}
