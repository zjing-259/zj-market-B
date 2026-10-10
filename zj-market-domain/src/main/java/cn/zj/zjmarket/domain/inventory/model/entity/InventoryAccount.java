package cn.zj.zjmarket.domain.inventory.model.entity;
import cn.zj.zjmarket.types.exception.InventoryFailure;
public record InventoryAccount(String goodsId,long available,long reserved,long sold,long version,long updatedAt) {
 public InventoryAccount { if(available<0 || reserved<0 || sold<0 || version<1)throw new IllegalArgumentException("Invalid inventory"); }
 private InventoryAccount next(long a,long r,long s,long now) { return new InventoryAccount(goodsId,a,r,s,Math.incrementExact(version),now); }
 public InventoryAccount adjust(long delta,long now) {long a=Math.addExact(available,delta);if(a<0)throw new InventoryFailure(409,"STOCK_INSUFFICIENT");return next(a,reserved,sold,now);}
 public InventoryAccount reserve(long q,long now) {positive(q);if(available<q)throw new InventoryFailure(409,"STOCK_INSUFFICIENT");return next(available-q,Math.addExact(reserved,q),sold,now);}
 public InventoryAccount release(long q,long now) {positive(q);if(reserved<q)throw new IllegalArgumentException("Reservation balance mismatch");return next(Math.addExact(available,q),reserved-q,sold,now);}
 public InventoryAccount confirm(long q,long now) {positive(q);if(reserved<q)throw new IllegalArgumentException("Reservation balance mismatch");return next(available,reserved-q,Math.addExact(sold,q),now);}
 private static void positive(long q){if(q<1)throw new IllegalArgumentException("Positive quantity required");}
}
