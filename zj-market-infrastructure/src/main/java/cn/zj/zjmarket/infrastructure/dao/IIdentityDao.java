package cn.zj.zjmarket.infrastructure.dao;

import cn.zj.zjmarket.domain.identity.model.entity.LoginGrant;
import cn.zj.zjmarket.domain.identity.model.entity.User;
import cn.zj.zjmarket.domain.identity.model.valobj.RefreshCredential;
import cn.zj.zjmarket.infrastructure.dao.po.UserRow;
import java.util.List;
import org.apache.ibatis.annotations.*;
public interface IIdentityDao {


    String USER_COLUMNS="user_id AS userId,login_name AS loginName,display_name AS displayName,password_hash AS passwordHash,enabled,auth_version AS authVersion";
    @Select("SELECT "+USER_COLUMNS+" FROM b_user WHERE login_name=#{login}") UserRow byLogin(String login);
    @Select("SELECT "+USER_COLUMNS+" FROM b_user WHERE user_id=#{id}") UserRow byId(String id);
    @Select("SELECT "+USER_COLUMNS+" FROM b_user WHERE user_id=#{id} FOR UPDATE") UserRow lockUser(String id);
    @Select("SELECT role FROM b_user_role WHERE user_id=#{id}") List<String> roles(String id);
    @Insert("INSERT INTO b_user(user_id,login_name,display_name,password_hash,enabled,auth_version) VALUES(#{userId},#{loginName},#{displayName},#{passwordHash},#{enabled},#{authVersion})") void insertUser(User user);
    @Insert("INSERT INTO b_user_role(user_id,role) VALUES(#{id},#{role})") void insertRole(@Param("id")String id,@Param("role")String role);
    @Select("SELECT grant_id AS grantId,user_id AS userId,auth_version AS authVersion,expires_at AS expiresAt,revoked FROM b_login_grant WHERE grant_id=#{id}") LoginGrant grant(String id);
    @Select("SELECT grant_id AS grantId,user_id AS userId,auth_version AS authVersion,expires_at AS expiresAt,revoked FROM b_login_grant WHERE grant_id=#{id} FOR UPDATE") LoginGrant lockGrant(String id);
    @Insert("INSERT INTO b_login_grant(grant_id,user_id,auth_version,expires_at,revoked) VALUES(#{grantId},#{userId},#{authVersion},#{expiresAt},#{revoked})") void insertGrant(LoginGrant grant);
    @Update("UPDATE b_login_grant SET revoked=TRUE WHERE grant_id=#{id}") void revoke(String id);
    @Select("SELECT digest,grant_id AS grantId,used FROM b_refresh_token WHERE digest=#{digest}") RefreshCredential refresh(String digest);
    @Insert("INSERT INTO b_refresh_token(digest,grant_id,used) VALUES(#{digest},#{grantId},#{used})") void insertRefresh(RefreshCredential token);
    @Update("UPDATE b_refresh_token SET used=TRUE WHERE digest=#{digest}") void useRefresh(String digest);
}
