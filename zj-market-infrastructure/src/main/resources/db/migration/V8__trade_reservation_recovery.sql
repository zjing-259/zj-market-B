ALTER TABLE b_market_order
 ADD a_evidence JSON NULL, ADD a_evidence_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
 ADD a_received_at_ms BIGINT NULL, ADD a_deadline_due_ms BIGINT NULL,
 ADD review_required BOOLEAN NOT NULL DEFAULT FALSE,
 ADD last_error VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
 ADD close_request JSON NULL, ADD close_request_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
 ADD close_reason VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NULL,
 ADD INDEX idx_order_a_deadline(business_status,a_deadline_due_ms,order_id),
 ADD CONSTRAINT ck_a_evidence_hash CHECK((a_evidence IS NULL AND a_evidence_hash IS NULL AND a_received_at_ms IS NULL) OR (a_evidence IS NOT NULL AND a_evidence_hash IS NOT NULL AND a_received_at_ms IS NOT NULL)),
 ADD CONSTRAINT ck_close_frozen CHECK((close_request IS NULL AND close_request_hash IS NULL AND close_reason IS NULL) OR (close_request IS NOT NULL AND close_request_hash IS NOT NULL AND close_reason IS NOT NULL));
CREATE TABLE b_trade_attempt (
 attempt_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 order_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 intent VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, intent_version BIGINT NOT NULL,
 token_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 request_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 method VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 started_at_ms BIGINT NOT NULL, finished_at_ms BIGINT NULL,
 code VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
 result_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL, stale BOOLEAN NOT NULL DEFAULT FALSE,
 FOREIGN KEY(order_id) REFERENCES b_trade_coordination(order_id),
 CHECK(method IN ('reserve','query')), CHECK(intent_version>0),
 INDEX idx_trade_attempt_order(order_id,started_at_ms,attempt_id)
);
