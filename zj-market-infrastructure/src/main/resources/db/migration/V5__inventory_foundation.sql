-- Apply during a controlled product-write window; do not run old product writers after V5.
CREATE TABLE b_inventory_account (
 goods_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 available BIGINT NOT NULL DEFAULT 0, reserved BIGINT NOT NULL DEFAULT 0, sold BIGINT NOT NULL DEFAULT 0,
 inventory_version BIGINT NOT NULL DEFAULT 1,
 initialized_by VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 created_at_ms BIGINT NOT NULL, updated_at_ms BIGINT NOT NULL,
 FOREIGN KEY(goods_id) REFERENCES b_product(goods_id),
 CHECK(available>=0 AND reserved>=0 AND sold>=0), CHECK(inventory_version>0)
);
INSERT INTO b_inventory_account(goods_id,initialized_by,created_at_ms,updated_at_ms)
 SELECT goods_id,'V5_BACKFILL',CAST(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3))*1000 AS SIGNED),CAST(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3))*1000 AS SIGNED) FROM b_product;
CREATE TABLE b_inventory_operation (
 operation_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 operator_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 operation_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 goods_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 kind VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 delta BIGINT NOT NULL, expected_version BIGINT NOT NULL, reason VARCHAR(256) NOT NULL,
 outcome VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 result_code VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 completed_at_ms BIGINT NOT NULL, result_available BIGINT NOT NULL,
 result_reserved BIGINT NOT NULL, result_sold BIGINT NOT NULL,
 result_version BIGINT NOT NULL, result_updated_at_ms BIGINT NOT NULL,
 UNIQUE KEY uk_inventory_operation(operator_id,operation_key),
 UNIQUE KEY uk_inventory_operation_goods(operation_id,goods_id),
 FOREIGN KEY(operator_id) REFERENCES b_user(user_id),
 FOREIGN KEY(goods_id) REFERENCES b_inventory_account(goods_id),
 CHECK(kind IN ('INBOUND','ADJUST')), CHECK(delta<>0 AND (kind<>'INBOUND' OR delta>0)),
 CHECK(expected_version>0 AND result_version>0),
 CHECK(outcome IN ('SUCCEEDED','REJECTED')),
 CHECK((outcome='SUCCEEDED' AND result_code='0000') OR (outcome='REJECTED' AND result_code<>'0000')),
 CHECK(result_available>=0 AND result_reserved>=0 AND result_sold>=0),
 INDEX idx_inventory_operation_goods(goods_id,completed_at_ms,operation_id)
);
CREATE TABLE b_inventory_ledger (
 ledger_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 goods_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 operation_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 kind VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 delta_available BIGINT NOT NULL, before_available BIGINT NOT NULL, after_available BIGINT NOT NULL,
 before_reserved BIGINT NOT NULL, after_reserved BIGINT NOT NULL,
 before_sold BIGINT NOT NULL, after_sold BIGINT NOT NULL,
 reason VARCHAR(256) NOT NULL, created_at_ms BIGINT NOT NULL,
 UNIQUE KEY uk_inventory_ledger_operation(operation_id),
 FOREIGN KEY(goods_id) REFERENCES b_inventory_account(goods_id),
 FOREIGN KEY(operation_id,goods_id) REFERENCES b_inventory_operation(operation_id,goods_id),
 CHECK(kind IN ('INBOUND','ADJUST')),
 CHECK(before_available>=0 AND after_available>=0 AND before_reserved>=0 AND after_reserved>=0 AND before_sold>=0 AND after_sold>=0),
 CHECK(after_available-before_available=delta_available AND delta_available<>0),
 CHECK(after_reserved=before_reserved AND after_sold=before_sold),
 INDEX idx_inventory_ledger_goods(goods_id,created_at_ms,ledger_id)
);
