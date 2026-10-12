CREATE TABLE b_user (
 user_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 login_name VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
 display_name VARCHAR(64) NOT NULL,
 password_hash VARCHAR(255) CHARACTER SET ascii NOT NULL,
 enabled BOOLEAN NOT NULL DEFAULT TRUE,
 auth_version BIGINT NOT NULL DEFAULT 1,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE b_user_role (
 user_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 role VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 PRIMARY KEY(user_id,role),
 FOREIGN KEY(user_id) REFERENCES b_user(user_id),
 CHECK(role IN ('USER','OPERATOR'))
);
CREATE TABLE b_login_grant (
 grant_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 user_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 auth_version BIGINT NOT NULL,
 expires_at BIGINT NOT NULL,
 revoked BOOLEAN NOT NULL DEFAULT FALSE,
 FOREIGN KEY(user_id) REFERENCES b_user(user_id),
 INDEX idx_grant_user(user_id)
);
CREATE TABLE b_refresh_token (
 digest CHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 grant_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 used BOOLEAN NOT NULL DEFAULT FALSE,
 FOREIGN KEY(grant_id) REFERENCES b_login_grant(grant_id),
 INDEX idx_refresh_grant(grant_id)
);
