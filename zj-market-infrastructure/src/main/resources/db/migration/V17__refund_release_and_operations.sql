ALTER TABLE b_market_order DROP CHECK ck_closed_basis,
 ADD CONSTRAINT ck_closed_basis CHECK((business_status='CLOSED' AND closed_at_ms IS NOT NULL AND close_basis IN ('LOCAL_NEVER_DISPATCHED','A_CONFIRMED','FULL_REFUND_CONFIRMED')) OR (business_status<>'CLOSED' AND closed_at_ms IS NULL AND close_basis IS NULL));
ALTER TABLE b_refund ADD release_status VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'HELD',
 ADD release_error VARCHAR(64), ADD CONSTRAINT ck_refund_release_status CHECK(release_status IN ('HELD','READY','RELEASED','ALREADY_RELEASED','REVIEW_REQUIRED'));
ALTER TABLE b_refund_task ADD check_only BOOLEAN NOT NULL DEFAULT FALSE, ADD check_previous_state VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin;
CREATE TABLE b_refund_release (
 order_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 refund_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
 payment_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 ledger_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 outcome VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 refund_fact_version BIGINT NOT NULL,
 eligibility_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 success_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 proof LONGBLOB NOT NULL, proof_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 released_at_ms BIGINT NOT NULL,
 FOREIGN KEY(refund_id,payment_id,order_id) REFERENCES b_refund(refund_id,payment_id,order_id),
 FOREIGN KEY(ledger_id) REFERENCES b_inventory_ledger(ledger_id),
 CHECK(outcome IN ('RELEASED','ALREADY_RELEASED') AND refund_fact_version>0)
);
CREATE TABLE b_refund_operation (
 actor_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 operation_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 refund_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 action VARCHAR(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 expected_version BIGINT NOT NULL, reason VARCHAR(256) NOT NULL,
 request_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 result LONGBLOB NOT NULL,result_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 created_at_ms BIGINT NOT NULL,
 PRIMARY KEY(actor_id,operation_id), FOREIGN KEY(actor_id) REFERENCES b_user(user_id),
 FOREIGN KEY(refund_id) REFERENCES b_refund(refund_id),
 CHECK(action IN ('CHECK','RETRY') AND expected_version>0)
);
