package cn.zj.zjmarket.domain.identity.model.valobj;

import java.security.*;
import java.util.*;
public record IdentityTokens(String accessToken,String tokenType,long expiresIn,UserView user,
                         String refreshToken,long refreshExpiresIn) {}
