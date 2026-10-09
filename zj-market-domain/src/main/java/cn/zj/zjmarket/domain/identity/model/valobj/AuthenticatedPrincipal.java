package cn.zj.zjmarket.domain.identity.model.valobj;

import java.security.*;
import java.util.*;
public record AuthenticatedPrincipal(UserView user,String grantId) {}
