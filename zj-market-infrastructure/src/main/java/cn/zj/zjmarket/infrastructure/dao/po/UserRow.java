package cn.zj.zjmarket.infrastructure.dao.po;

import org.apache.ibatis.annotations.*;
public record UserRow(String userId,String loginName,String displayName,String passwordHash,boolean enabled,long authVersion) {}
