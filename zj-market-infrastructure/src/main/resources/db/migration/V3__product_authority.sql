CREATE TABLE b_product (
 goods_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 goods_name VARCHAR(128) NOT NULL,
 description VARCHAR(2000) NOT NULL,
 image_url VARCHAR(2048) NULL,
 original_price DECIMAL(8,2) NOT NULL,
 currency CHAR(3) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 sale_status VARCHAR(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 product_version BIGINT NOT NULL,
 created_at_ms BIGINT NOT NULL,
 updated_at_ms BIGINT NOT NULL,
 CHECK (original_price >= 0.01 AND original_price <= 999999.99),
 CHECK (currency='CNY'), CHECK (sale_status IN ('ON_SALE','OFF_SALE')), CHECK (product_version>0),
 INDEX idx_product_listing (sale_status,created_at_ms,goods_id)
);
CREATE TABLE b_product_outbox (
 event_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 goods_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 product_version BIGINT NOT NULL,
 event_type VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 body LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
 delivery_state VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'PENDING',
 created_at_ms BIGINT NOT NULL,
 UNIQUE KEY uk_product_fact (goods_id,product_version),
 FOREIGN KEY (goods_id) REFERENCES b_product(goods_id),
 CHECK (event_type='PRODUCT_SNAPSHOT_CHANGED'), CHECK (product_version>0), CHECK (JSON_VALID(body)),
 INDEX idx_outbox_pending (delivery_state,created_at_ms,event_id)
);
CREATE TABLE b_product_sync (
 goods_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 target_version BIGINT NOT NULL,
 target_event_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 confirmed_version BIGINT NULL,
 state VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 last_error VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin NULL,
 checked_at VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NULL,
 FOREIGN KEY (goods_id) REFERENCES b_product(goods_id),
 FOREIGN KEY (target_event_id) REFERENCES b_product_outbox(event_id),
 CHECK (target_version>0), CHECK (confirmed_version IS NULL OR confirmed_version>0),
 CHECK (state IN ('PENDING','CONFIRMED','REJECTED','RECONCILIATION_REQUIRED'))
);
