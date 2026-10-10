package cn.zj.zjmarket.types.exception;
public final class InventoryFailure extends RuntimeException {
 private final int status;private final String code;
 public InventoryFailure(int status,String code){super(code);this.status=status;this.code=code;}
 public int status(){return status;} public String code(){return code;}
}
