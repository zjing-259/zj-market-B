ALTER TABLE b_product_outbox
 ADD body_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
 ADD snapshot_sale_status VARCHAR(8) CHARACTER SET ascii COLLATE ascii_bin NULL,
 ADD send_attempts INT NOT NULL DEFAULT 0,
 ADD send_failures INT NOT NULL DEFAULT 0,
 ADD query_attempts INT NOT NULL DEFAULT 0,
 ADD next_send_ms BIGINT NOT NULL DEFAULT 0,
 ADD next_query_ms BIGINT NOT NULL DEFAULT 0,
 ADD lease_token VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
 ADD lease_until_ms BIGINT NOT NULL DEFAULT 0,
 ADD paused BOOLEAN NOT NULL DEFAULT FALSE,
 ADD processing_state VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'WAITING',
 ADD result_body LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL,
 ADD result_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
 ADD outcome VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NULL,
 ADD result_code VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin NULL,
 ADD last_error VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin NULL;
UPDATE b_product_outbox SET body_hash=SHA2(body,256),snapshot_sale_status=JSON_UNQUOTE(JSON_EXTRACT(body,'$.payload.saleStatus'));
ALTER TABLE b_product_outbox MODIFY body_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 MODIFY snapshot_sale_status VARCHAR(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 ADD INDEX idx_sync_send (processing_state,paused,delivery_state,next_send_ms,lease_until_ms),
 ADD INDEX idx_sync_query (processing_state,paused,next_query_ms,lease_until_ms);
CREATE TABLE b_sync_inbox (
 consumer VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 producer VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 event_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 body_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 original_event_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 processing_outcome VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 result_body LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
 processed_at_ms BIGINT NOT NULL,
 PRIMARY KEY (consumer,producer,event_id)
);
CREATE TABLE b_sync_quarantine (
 quarantine_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 dedup_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
 body_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 topic VARCHAR(255) NOT NULL,
 tag VARCHAR(128) NULL,
 key_id VARCHAR(128) NULL,
 signature VARCHAR(256) NULL,
 body LONGBLOB NOT NULL,
 original_size INT NOT NULL,
 reason VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 stored_at_ms BIGINT NOT NULL,
 replayed_at_ms BIGINT NULL,
 INDEX idx_quarantine_time (stored_at_ms,quarantine_id)
);
CREATE TABLE b_sync_audit (
 audit_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 goods_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 event_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 operator_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 action VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 occurred_at_ms BIGINT NOT NULL,
 INDEX idx_sync_audit_goods (goods_id,occurred_at_ms)
);
