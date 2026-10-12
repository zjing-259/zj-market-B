-- B-05.3 additive migration. V14 remains immutable. No original payment or inventory facts change.
ALTER TABLE b_refund DROP CHECK ck_refund_funds,
 ADD CONSTRAINT ck_refund_funds_v15 CHECK(funds_status IN ('NONE','PENDING','UNKNOWN','FAILED','SUCCEEDED')),
 ADD COLUMN current_attempt_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 ADD COLUMN fact_version BIGINT NOT NULL DEFAULT 0,
 ADD COLUMN success_fact LONGBLOB, ADD COLUMN success_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 ADD COLUMN refunded_at_ms BIGINT,
 ADD CONSTRAINT ck_refund_success_v15 CHECK((funds_status='SUCCEEDED' AND success_fact IS NOT NULL AND success_hash IS NOT NULL AND refunded_at_ms IS NOT NULL) OR (funds_status<>'SUCCEEDED' AND success_fact IS NULL AND success_hash IS NULL AND refunded_at_ms IS NULL)),
 ADD CONSTRAINT ck_refund_version_v15 CHECK(fact_version>=0);
CREATE TABLE b_refund_attempt (
 attempt_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 refund_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,attempt_no INT NOT NULL,
 request LONGBLOB NOT NULL,request_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 state VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'PENDING',
 possible_sent BOOLEAN NOT NULL DEFAULT FALSE,
 pending_version BIGINT NOT NULL,pending_fact LONGBLOB NOT NULL,pending_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 result_version BIGINT,result_fact LONGBLOB,result_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 created_at_ms BIGINT NOT NULL,updated_at_ms BIGINT NOT NULL,
 UNIQUE KEY uk_refund_attempt_parent(refund_id,attempt_id),UNIQUE KEY uk_refund_attempt_no(refund_id,attempt_no),
 CONSTRAINT fk_refund_attempt_root FOREIGN KEY(refund_id) REFERENCES b_refund(refund_id),
 CONSTRAINT ck_refund_attempt_state CHECK(state IN ('PENDING','UNKNOWN','FAILED','SUCCEEDED')),
 CONSTRAINT ck_refund_attempt_version CHECK(attempt_no>0 AND pending_version>0 AND (result_version IS NULL OR result_version>pending_version)),
 CONSTRAINT ck_refund_attempt_result CHECK((state IN ('FAILED','SUCCEEDED') AND result_version IS NOT NULL AND result_fact IS NOT NULL AND result_hash IS NOT NULL) OR (state IN ('PENDING','UNKNOWN') AND result_version IS NULL AND result_fact IS NULL AND result_hash IS NULL))
);
ALTER TABLE b_refund ADD CONSTRAINT fk_refund_current_v15 FOREIGN KEY(refund_id,current_attempt_id) REFERENCES b_refund_attempt(refund_id,attempt_id);
CREATE TABLE b_refund_task (
 refund_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 state VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'READY',intent_version BIGINT NOT NULL DEFAULT 1,
 next_attempt_ms BIGINT NOT NULL,lease_token VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,lease_until_ms BIGINT,
 failure_count INT NOT NULL DEFAULT 0,business_failures INT NOT NULL DEFAULT 0,alerted BOOLEAN NOT NULL DEFAULT FALSE,last_error VARCHAR(64),created_at_ms BIGINT NOT NULL,updated_at_ms BIGINT NOT NULL,
 CONSTRAINT fk_refund_task_root FOREIGN KEY(refund_id) REFERENCES b_refund(refund_id),
 CONSTRAINT ck_refund_task_state CHECK(state IN ('READY','LEASED','WAITING_DEPENDENCY','REVIEW_REQUIRED','DONE')),
 CONSTRAINT ck_refund_task_lease CHECK((lease_token IS NULL)=(lease_until_ms IS NULL)),
 CONSTRAINT ck_refund_task_counts CHECK(intent_version>0 AND failure_count>=0 AND business_failures>=0),
 INDEX idx_refund_task_due(state,next_attempt_ms,lease_until_ms)
);
CREATE TABLE b_sim_refund (
 refund_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 payment_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 amount DECIMAL(10,2) NOT NULL,currency CHAR(3) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 root_request LONGBLOB NOT NULL,root_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 refunded_amount DECIMAL(10,2) NOT NULL DEFAULT 0,success_attempt_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,created_at_ms BIGINT NOT NULL,
 UNIQUE KEY uk_sim_refund_payment(payment_id),
 CONSTRAINT fk_sim_refund_payment FOREIGN KEY(payment_id) REFERENCES b_sim_payment(payment_id),
 CONSTRAINT ck_sim_refund_amount CHECK(amount>0 AND currency='CNY' AND refunded_amount>=0 AND refunded_amount<=amount),
 CONSTRAINT ck_sim_refund_success CHECK((refunded_amount=0 AND success_attempt_id IS NULL) OR (refunded_amount=amount AND success_attempt_id IS NOT NULL))
);
CREATE TABLE b_sim_refund_attempt (
 attempt_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,refund_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,attempt_no INT NOT NULL,
 request LONGBLOB NOT NULL,request_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 state VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,fact LONGBLOB NOT NULL,fact_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 success_slot TINYINT GENERATED ALWAYS AS (CASE WHEN state='SUCCEEDED' THEN 1 ELSE NULL END) STORED,
 UNIQUE KEY uk_sim_refund_attempt_parent(refund_id,attempt_id),UNIQUE KEY uk_sim_refund_attempt_no(refund_id,attempt_no),UNIQUE KEY uk_sim_refund_success(refund_id,success_slot),
 CONSTRAINT fk_sim_refund_attempt_root FOREIGN KEY(refund_id) REFERENCES b_sim_refund(refund_id),
 CONSTRAINT ck_sim_refund_attempt_state CHECK(state IN ('UNKNOWN','FAILED','SUCCEEDED') AND attempt_no>0)
);
ALTER TABLE b_sim_refund ADD CONSTRAINT fk_sim_refund_success FOREIGN KEY(refund_id,success_attempt_id) REFERENCES b_sim_refund_attempt(refund_id,attempt_id);
CREATE TABLE b_sim_refund_notification (
 notification_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,refund_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,attempt_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 fact_version BIGINT NOT NULL DEFAULT 1,state VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'READY',next_attempt_ms BIGINT NOT NULL,
 lease_token VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,lease_until_ms BIGINT,failure_count INT NOT NULL DEFAULT 0,alerted BOOLEAN NOT NULL DEFAULT FALSE,created_at_ms BIGINT NOT NULL,
 UNIQUE KEY uk_sim_refund_notice_fact(attempt_id,fact_version),
 CONSTRAINT fk_sim_refund_notice_attempt FOREIGN KEY(refund_id,attempt_id) REFERENCES b_sim_refund_attempt(refund_id,attempt_id),
 CONSTRAINT ck_sim_refund_notice_state CHECK(state IN ('READY','LEASED','DONE','REVIEW_REQUIRED')),
 CONSTRAINT ck_sim_refund_notice_lease CHECK((lease_token IS NULL)=(lease_until_ms IS NULL)),
 CONSTRAINT ck_sim_refund_notice_counts CHECK(fact_version>0 AND failure_count>=0),INDEX idx_sim_refund_notice_due(state,next_attempt_ms,lease_until_ms)
);
