package cn.zj.zjmarket.infrastructure.dao.po;

import org.apache.ibatis.annotations.*;
public record SyncInboxRow(String bodyHash,String originalEventId){}
