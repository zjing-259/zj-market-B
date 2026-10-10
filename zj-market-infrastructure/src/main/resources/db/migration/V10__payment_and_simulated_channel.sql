-- Resolve the historical unnamed status CHECK from metadata, never infer its ordinal.
SET @b_status_check = (SELECT tc.CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS tc JOIN information_schema.CHECK_CONSTRAINTS cc ON cc.CONSTRAINT_SCHEMA=tc.CONSTRAINT_SCHEMA AND cc.CONSTRAINT_NAME=tc.CONSTRAINT_NAME WHERE tc.TABLE_SCHEMA=DATABASE() AND tc.TABLE_NAME='b_market_order' AND cc.CHECK_CLAUSE LIKE '%WAITING_PAYMENT%' AND cc.CHECK_CLAUSE LIKE '%PROCESSING%');
SET @b_drop_status = CONCAT('ALTER TABLE b_market_order DROP CHECK `',@b_status_check,'`');
PREPARE b_status_stmt FROM @b_drop_status;
EXECUTE b_status_stmt;
DEALLOCATE PREPARE b_status_stmt;
ALTER TABLE b_market_order ADD CONSTRAINT ck_order_status_v10 CHECK(business_status IN ('PROCESSING','WAITING_PAYMENT','PAYMENT_PROCESSING','PAID_WAITING_A','PAID_WAITING_TEAM','GROUP_COMPLETED','WAITING_REFUND','CLOSING','CLOSED')), ADD CONSTRAINT ck_payment_exposure_v10 CHECK(payment_exposure IN ('NEVER_OPENED','POSSIBLY_OPENED'));
CREATE TABLE b_payment (
 payment_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 order_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 user_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 goods_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 snapshot JSON NOT NULL, snapshot_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 amount DECIMAL(8,2) NOT NULL, currency CHAR(3) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'CNY',
 reserved_at_ms BIGINT NOT NULL, payment_deadline_ms BIGINT NOT NULL,
 funds_state VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'UNPAID',
 gate VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'OPEN',
 a_acceptance VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'NOT_SENT',
 active_attempt_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin, success_attempt_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 paid_at_ms BIGINT, version BIGINT NOT NULL DEFAULT 1, review_required BOOLEAN NOT NULL DEFAULT FALSE,
 last_error VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin, created_at_ms BIGINT NOT NULL, updated_at_ms BIGINT NOT NULL,
 UNIQUE KEY uk_payment_order(order_id),
 FOREIGN KEY(order_id,user_id,goods_id) REFERENCES b_market_order(order_id,user_id,goods_id),
 CHECK(amount>=0.01 AND currency='CNY' AND payment_deadline_ms>reserved_at_ms AND version>0),
 CHECK(funds_state IN ('UNPAID','UNKNOWN','SUCCEEDED')), CHECK(gate IN ('OPEN','CLOSING','CLOSED_UNPAID','PAID')),
 CHECK(a_acceptance IN ('NOT_SENT','PENDING','ACCEPTED','REJECTED','REVIEW_REQUIRED')),
 CHECK((funds_state='SUCCEEDED' AND paid_at_ms IS NOT NULL AND success_attempt_id IS NOT NULL) OR (funds_state<>'SUCCEEDED' AND paid_at_ms IS NULL AND success_attempt_id IS NULL)),
 INDEX idx_payment_owner(user_id,created_at_ms,payment_id)
);
CREATE TABLE b_payment_attempt (
 attempt_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 payment_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 attempt_no INT NOT NULL, previous_attempt_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 request_json JSON NOT NULL, request_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 state VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'CREATING',
 amount DECIMAL(8,2) NOT NULL, payment_deadline_ms BIGINT NOT NULL,
 channel_transaction_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin, paid_at_ms BIGINT,
 version BIGINT NOT NULL DEFAULT 1, last_error VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 created_at_ms BIGINT NOT NULL, updated_at_ms BIGINT NOT NULL,
 FOREIGN KEY(payment_id) REFERENCES b_payment(payment_id),
 UNIQUE KEY uk_attempt_number(payment_id,attempt_no), UNIQUE KEY uk_attempt_parent(payment_id,attempt_id),
 FOREIGN KEY(payment_id,previous_attempt_id) REFERENCES b_payment_attempt(payment_id,attempt_id),
 CHECK(attempt_no>0 AND version>0 AND amount>=0.01),
 CHECK(state IN ('CREATING','OPEN','UNKNOWN','FAILED','SUCCEEDED','CLOSED_UNPAID')),
 CHECK((state='SUCCEEDED' AND paid_at_ms IS NOT NULL) OR (state<>'SUCCEEDED' AND paid_at_ms IS NULL))
);
ALTER TABLE b_payment ADD CONSTRAINT fk_payment_active FOREIGN KEY(payment_id,active_attempt_id) REFERENCES b_payment_attempt(payment_id,attempt_id), ADD CONSTRAINT fk_payment_success FOREIGN KEY(payment_id,success_attempt_id) REFERENCES b_payment_attempt(payment_id,attempt_id);
CREATE TABLE b_payment_operation (
 operation_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 actor_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, operation_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 order_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 payment_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin, attempt_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 action VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, chosen_result VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin,
 request_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, receipt_json JSON NOT NULL,
 progress VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, created_at_ms BIGINT NOT NULL,
 UNIQUE KEY uk_payment_operation(actor_id,operation_key), FOREIGN KEY(actor_id) REFERENCES b_user(user_id), FOREIGN KEY(order_id) REFERENCES b_market_order(order_id), FOREIGN KEY(payment_id,attempt_id) REFERENCES b_payment_attempt(payment_id,attempt_id),
 CHECK(action IN ('CREATE_ATTEMPT','CHOOSE_RESULT')), CHECK(chosen_result IS NULL OR chosen_result IN ('SUCCEEDED','FAILED')),
 CHECK(progress IN ('PENDING','APPLIED','REJECTED','WAITING_DEPENDENCY','REVIEW_REQUIRED')),
 INDEX idx_payment_operation_attempt(payment_id,attempt_id,action)
);
CREATE TABLE b_payment_task (
 payment_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 attempt_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 action VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, chosen_result VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin,
 intent_version BIGINT NOT NULL DEFAULT 1, state VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 next_attempt_ms BIGINT NOT NULL, lease_token VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin, lease_until_ms BIGINT,
 failure_count BIGINT NOT NULL DEFAULT 0, last_error VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 FOREIGN KEY(payment_id,attempt_id) REFERENCES b_payment_attempt(payment_id,attempt_id),
 CHECK(state IN ('READY','LEASED','DONE','WAITING_DEPENDENCY','REVIEW_REQUIRED')), CHECK(intent_version>0 AND failure_count>=0),
 CHECK((lease_token IS NULL AND lease_until_ms IS NULL) OR (lease_token IS NOT NULL AND lease_until_ms IS NOT NULL)),
 INDEX idx_payment_task_due(state,next_attempt_ms,lease_until_ms,payment_id)
);
CREATE TABLE b_sim_payment (
 payment_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 gate VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'OPEN',
 amount DECIMAL(8,2) NOT NULL, currency CHAR(3) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'CNY',
 reserved_at_ms BIGINT NOT NULL, payment_deadline_ms BIGINT NOT NULL,
 snapshot_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 success_attempt_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin, closed_at_ms BIGINT,
 version BIGINT NOT NULL DEFAULT 1, created_at_ms BIGINT NOT NULL,
 FOREIGN KEY(payment_id) REFERENCES b_payment(payment_id),
 CHECK(gate IN ('OPEN','PAID','CLOSED_UNPAID')), CHECK(amount>=0.01 AND currency='CNY' AND payment_deadline_ms>reserved_at_ms),
 CHECK((gate='PAID' AND success_attempt_id IS NOT NULL) OR (gate<>'PAID' AND success_attempt_id IS NULL)),
 CHECK((gate='CLOSED_UNPAID' AND closed_at_ms IS NOT NULL) OR (gate<>'CLOSED_UNPAID' AND closed_at_ms IS NULL))
);
CREATE TABLE b_sim_attempt (
 attempt_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 payment_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 attempt_no INT NOT NULL, channel_transaction_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 state VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'OPEN',
 request_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, paid_at_ms BIGINT, created_at_ms BIGINT NOT NULL,
 success_slot TINYINT GENERATED ALWAYS AS (CASE WHEN state='SUCCEEDED' THEN 1 ELSE NULL END) STORED,
 UNIQUE KEY uk_sim_attempt_parent(payment_id,attempt_id), UNIQUE KEY uk_sim_attempt_no(payment_id,attempt_no),
 UNIQUE KEY uk_sim_success(payment_id,success_slot), UNIQUE KEY uk_sim_transaction(channel_transaction_id),
 FOREIGN KEY(payment_id) REFERENCES b_sim_payment(payment_id), FOREIGN KEY(payment_id,attempt_id) REFERENCES b_payment_attempt(payment_id,attempt_id),
 CHECK(state IN ('OPEN','FAILED','SUCCEEDED','CLOSED_UNPAID')),
 CHECK((state='SUCCEEDED' AND paid_at_ms IS NOT NULL) OR (state<>'SUCCEEDED' AND paid_at_ms IS NULL))
);
ALTER TABLE b_sim_payment ADD CONSTRAINT fk_sim_success FOREIGN KEY(payment_id,success_attempt_id) REFERENCES b_sim_attempt(payment_id,attempt_id);
CREATE TABLE b_sim_operation (
 payment_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, attempt_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 action VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, request_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 result_json JSON NOT NULL, created_at_ms BIGINT NOT NULL,
 PRIMARY KEY(payment_id,attempt_id,action), FOREIGN KEY(payment_id,attempt_id) REFERENCES b_sim_attempt(payment_id,attempt_id), CHECK(action IN ('CREATE_ATTEMPT','CHOOSE_RESULT'))
);
CREATE TABLE b_sim_notification (
 notification_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 payment_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, attempt_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 fact_json JSON NOT NULL, fact_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 state VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'READY',
 next_attempt_ms BIGINT NOT NULL, created_at_ms BIGINT NOT NULL,
 UNIQUE KEY uk_sim_notification(payment_id,attempt_id), FOREIGN KEY(payment_id,attempt_id) REFERENCES b_sim_attempt(payment_id,attempt_id),
 CHECK(state IN ('READY','LEASED','DONE','REVIEW_REQUIRED')), INDEX idx_sim_notification_due(state,next_attempt_ms,notification_id)
);
