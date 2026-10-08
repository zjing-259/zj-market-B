package cn.zj.zjmarket.trigger.identity;
public record ApiResponse(String code,String message,Object data,String requestId) {
    public static ApiResponse ok(Object data,String requestId){return new ApiResponse("0000","成功",data,requestId);}
    public static ApiResponse error(String code,String requestId){return new ApiResponse(code,code,null,requestId);}
}
