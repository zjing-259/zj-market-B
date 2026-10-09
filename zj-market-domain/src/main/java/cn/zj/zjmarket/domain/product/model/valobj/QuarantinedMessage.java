package cn.zj.zjmarket.domain.product.model.valobj;

import java.util.*;
public record QuarantinedMessage(String quarantineId,String bodyHash,String reason,int originalSize,long storedAt,String state){}
