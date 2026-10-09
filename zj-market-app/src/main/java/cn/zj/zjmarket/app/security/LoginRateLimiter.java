package cn.zj.zjmarket.app.security;

import cn.zj.zjmarket.types.exception.AuthFailure;
import java.util.*;
public final class LoginRateLimiter {
    private record Bucket(long reset,int count) {}
    private final Map<String,Bucket> buckets=new HashMap<>();
    private final int ipLimit,loginLimit;private final long windowMillis;
    public LoginRateLimiter(int ipLimit,int loginLimit,long windowSeconds){
        if(ipLimit<1 || loginLimit<1 || windowSeconds<1 || windowSeconds>3600)throw new IllegalArgumentException("Invalid login rate limits");
        this.ipLimit=ipLimit;this.loginLimit=loginLimit;windowMillis=windowSeconds*1000;
    }
    public synchronized void check(String ip,String name){
        long now=System.currentTimeMillis();buckets.entrySet().removeIf(e -> e.getValue().reset()<=now);
        if(buckets.size()>=10000)throw new AuthFailure(429,"RATE_LIMITED",windowMillis/1000);
        take("ip:"+ip,ipLimit,now);
        if(name!=null && name.matches("^[a-z0-9][a-z0-9._-]{2,31}$"))take("name:"+name,loginLimit,now);
    }
    private void take(String key,int limit,long now){
        Bucket b=buckets.get(key);if(b!=null && b.count()>=limit)throw new AuthFailure(429,"RATE_LIMITED",Math.max(1,(b.reset()-now+999)/1000));
        buckets.put(key,new Bucket(b==null?now+windowMillis:b.reset(),b==null?1:b.count()+1));
    }
}
