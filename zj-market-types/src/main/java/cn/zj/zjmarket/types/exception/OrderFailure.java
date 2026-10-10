package cn.zj.zjmarket.types.exception;
public final class OrderFailure extends RuntimeException {
 private final int status; private final String code; private final Object detail;
 public OrderFailure(int status,String code){this(status,code,null);}
 public OrderFailure(int status,String code,Object detail){super(code);this.status=status;this.code=code;this.detail=detail;}
 public Object detail(){return detail;} public int status(){return status;} public String code(){return code;}
}
