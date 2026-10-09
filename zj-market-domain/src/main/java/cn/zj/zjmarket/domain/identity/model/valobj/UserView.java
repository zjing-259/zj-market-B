package cn.zj.zjmarket.domain.identity.model.valobj;

import java.util.Set;
public record UserView(String userId, String loginName, String displayName, Set<String> roles) {}
