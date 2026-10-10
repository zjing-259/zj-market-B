package cn.zj.zjmarket.domain.inventory.model.valobj;
import cn.zj.zjmarket.types.exception.InventoryFailure;
public record InventoryRequest(String kind,String goodsId,long delta,long expectedVersion,String reason) {
 public InventoryRequest {
  if(!("INBOUND".equals(kind)||"ADJUST".equals(kind)) || goodsId==null || !goodsId.matches("[A-Za-z0-9][A-Za-z0-9_-]{0,63}") ||
   delta==0 || "INBOUND".equals(kind)&&delta<0 || expectedVersion<1 || reason==null || reason.isBlank() || reason.length()>256 ||
   reason.chars().anyMatch(Character::isISOControl) || reason.matches("(?s).*<\\s*/?\\s*[A-Za-z][^>]*>.*"))throw new InventoryFailure(400,"VALIDATION_FAILED");
 }
}
