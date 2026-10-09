package cn.zj.zjmarket.domain.product.model.valobj;

import java.util.*;
public record SyncBadMessage(String topic,String tag,String keyId,String signature,byte[] body,String reason){}
