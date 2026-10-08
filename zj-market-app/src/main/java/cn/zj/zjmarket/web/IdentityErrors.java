package cn.zj.zjmarket.web;
import cn.zj.zjmarket.application.identity.AuthFailure;
import cn.zj.zjmarket.trigger.identity.ApiResponse;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.dao.DataAccessException;
import org.springframework.transaction.TransactionException;
@RestControllerAdvice
public class IdentityErrors {
    @ExceptionHandler(cn.zj.zjmarket.application.product.ProductFailure.class) ResponseEntity<ApiResponse> product(cn.zj.zjmarket.application.product.ProductFailure e,HttpServletRequest req){return ResponseEntity.status(e.status()).body(ApiResponse.error(e.code(),id(req)));}
    @ExceptionHandler(cn.zj.zjmarket.application.product.SyncTransport.Failure.class) ResponseEntity<ApiResponse> sync(cn.zj.zjmarket.application.product.SyncTransport.Failure e,HttpServletRequest req){boolean upstream=e.code().equals("INTEGRATION_AUTH_FAILED") || e.permanent();return ResponseEntity.status(upstream?502:503).body(ApiResponse.error(upstream?"UPSTREAM_RESPONSE_INVALID":"DEPENDENCY_UNAVAILABLE",id(req)));}
    @ExceptionHandler(AuthFailure.class) ResponseEntity<ApiResponse> auth(AuthFailure e,HttpServletRequest req){
        var builder=ResponseEntity.status(e.status()).header("Cache-Control","no-store");
        if(e.status()==429)builder.header("Retry-After",Long.toString(Math.max(1,e.retryAfter())));
        if(e.status()==401)builder.header("WWW-Authenticate","Bearer");
        return builder.body(ApiResponse.error(e.code(),id(req)));
    }
    @ExceptionHandler(HttpMessageNotReadableException.class) ResponseEntity<ApiResponse> invalid(Exception e,HttpServletRequest req){return ResponseEntity.badRequest().body(ApiResponse.error("VALIDATION_FAILED",id(req)));}
    @ExceptionHandler({DataAccessException.class,TransactionException.class}) ResponseEntity<ApiResponse> database(Exception e,HttpServletRequest req){return ResponseEntity.status(503).body(ApiResponse.error("DEPENDENCY_UNAVAILABLE",id(req)));}
    @ExceptionHandler({org.springframework.web.servlet.resource.NoResourceFoundException.class,org.springframework.web.servlet.NoHandlerFoundException.class})
    ResponseEntity<ApiResponse> missing(Exception e,HttpServletRequest req){return ResponseEntity.status(404).body(ApiResponse.error("RESOURCE_NOT_FOUND",id(req)));}
    @ExceptionHandler(org.springframework.web.HttpRequestMethodNotSupportedException.class)
    ResponseEntity<ApiResponse> method(Exception e,HttpServletRequest req){return ResponseEntity.status(405).body(ApiResponse.error("METHOD_NOT_ALLOWED",id(req)));}
    @ExceptionHandler(org.springframework.web.HttpMediaTypeNotSupportedException.class)
    ResponseEntity<ApiResponse> media(Exception e,HttpServletRequest req){return ResponseEntity.status(415).body(ApiResponse.error("UNSUPPORTED_MEDIA_TYPE",id(req)));}
    @ExceptionHandler(Exception.class) ResponseEntity<ApiResponse> other(Exception e,HttpServletRequest req){return ResponseEntity.internalServerError().body(ApiResponse.error("INTERNAL_ERROR",id(req)));}
    private static String id(HttpServletRequest req){return (String)req.getAttribute("b.requestId");}
}
