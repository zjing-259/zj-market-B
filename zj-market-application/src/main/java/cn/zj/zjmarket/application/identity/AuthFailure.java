package cn.zj.zjmarket.application.identity;
public final class AuthFailure extends RuntimeException {
    private final int status;
    private final String code;
    private final long retryAfter;
    public AuthFailure(int status,String code){this(status,code,0);}
    public AuthFailure(int status,String code,long retryAfter){super(code);this.status=status;this.code=code;this.retryAfter=retryAfter;}
    public long retryAfter(){return retryAfter;}
    public int status() { return status; }
    public String code() { return code; }
}
