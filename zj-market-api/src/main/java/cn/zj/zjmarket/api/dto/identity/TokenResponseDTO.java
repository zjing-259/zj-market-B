package cn.zj.zjmarket.api.dto.identity;

public record TokenResponseDTO(String accessToken,String tokenType,long expiresIn,Object user) {}
