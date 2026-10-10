ALTER TABLE b_market_order
 ADD closed_at_ms BIGINT NULL, ADD close_basis VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NULL,
 ADD close_evidence JSON NULL, ADD close_evidence_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
 ADD CONSTRAINT ck_closed_basis CHECK((business_status='CLOSED' AND closed_at_ms IS NOT NULL AND close_basis IN ('LOCAL_NEVER_DISPATCHED','A_CONFIRMED')) OR (business_status<>'CLOSED' AND closed_at_ms IS NULL AND close_basis IS NULL)),
 ADD CONSTRAINT ck_close_evidence CHECK((close_evidence IS NULL AND close_evidence_hash IS NULL) OR (close_evidence IS NOT NULL AND close_evidence_hash IS NOT NULL));
ALTER TABLE b_trade_coordination ADD auth_check_required BOOLEAN NOT NULL DEFAULT FALSE, ADD auth_probe BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE b_trade_attempt DROP CHECK b_trade_attempt_chk_1, ADD CONSTRAINT ck_trade_attempt_method CHECK(method IN ('reserve','query','close'));
CREATE TABLE b_order_operation (
 operation_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 actor_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 operation_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 order_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 action VARCHAR(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 request_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 expected_version BIGINT NULL, reason VARCHAR(256) NOT NULL,
 result_json JSON NOT NULL, result_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, created_at_ms BIGINT NOT NULL,
 FOREIGN KEY(actor_id) REFERENCES b_user(user_id), FOREIGN KEY(order_id) REFERENCES b_market_order(order_id),
 UNIQUE KEY uk_order_operation(actor_id,action,operation_key), INDEX idx_order_operation(order_id,created_at_ms,operation_id),
 CHECK(action IN ('CANCEL','PAUSE','RESUME','CHECK')), CHECK(expected_version IS NULL OR expected_version>0)
);
