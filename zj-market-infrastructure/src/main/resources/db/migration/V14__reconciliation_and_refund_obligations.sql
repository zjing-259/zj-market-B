-- Additive B-05.2 only. No historical evidence or funds are rewritten.
CREATE TABLE b_reconciliation_task (
 task_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 source VARCHAR(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,channel VARCHAR(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,team_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 reconciliation_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,roster_version VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 state VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'DISCOVERED',
 roster LONGBLOB,roster_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin,team_proof LONGBLOB,team_proof_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 team_version BIGINT,terminal_status VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin,
 intent_version BIGINT NOT NULL DEFAULT 1,lease_token VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,lease_until_ms BIGINT,
 next_attempt_ms BIGINT NOT NULL,failure_count INT NOT NULL DEFAULT 0,alerted BOOLEAN NOT NULL DEFAULT FALSE,last_error VARCHAR(64),created_at_ms BIGINT NOT NULL,updated_at_ms BIGINT NOT NULL,
 UNIQUE KEY uk_recon_team(source,channel,team_id),UNIQUE KEY uk_recon_roster(source,channel,team_id,reconciliation_id,roster_version),
 CONSTRAINT ck_recon_state CHECK(state IN ('DISCOVERED','COLLECTING','READY','SUBMITTING','SUBMIT_UNKNOWN','WAITING_DEPENDENCY','RESOLVED','REVIEW_REQUIRED')),
 CONSTRAINT ck_recon_pair CHECK((lease_token IS NULL)=(lease_until_ms IS NULL)),CONSTRAINT ck_recon_roster CHECK((roster IS NULL)=(roster_hash IS NULL) AND (roster IS NULL)=(reconciliation_id IS NULL) AND (roster IS NULL)=(roster_version IS NULL)),
 CONSTRAINT ck_recon_version CHECK(intent_version>0 AND failure_count>=0 AND (team_version IS NULL OR team_version>0)),
 INDEX idx_recon_due(state,next_attempt_ms,lease_until_ms)
);
CREATE TABLE b_reconciliation_member (
 task_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,out_trade_no VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,user_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 local_order_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 state VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'WAITING',frozen LONGBLOB NOT NULL,frozen_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 proof LONGBLOB,proof_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin,decision LONGBLOB,decision_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 proof_version BIGINT NOT NULL DEFAULT 1,finalized BOOLEAN NOT NULL DEFAULT FALSE,last_error VARCHAR(64),updated_at_ms BIGINT NOT NULL,
 PRIMARY KEY(task_id,out_trade_no),CONSTRAINT fk_recon_member_task FOREIGN KEY(task_id) REFERENCES b_reconciliation_task(task_id),
 CONSTRAINT ck_recon_member_state CHECK(state IN ('WAITING','PAID_ACCEPTED','CLOSED_UNPAID','PAID_OUTSIDE_WINDOW','MISSING_LOCAL','UNKNOWN','REVIEW_REQUIRED')),
 CONSTRAINT ck_recon_member_proof CHECK((proof IS NULL)=(proof_hash IS NULL) AND (decision IS NULL)=(decision_hash IS NULL) AND proof_version>0),
 INDEX idx_recon_member_progress(task_id,state,updated_at_ms,out_trade_no)
);
CREATE TABLE b_reconciliation_submission (
 completion_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,task_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 state VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'FROZEN',request LONGBLOB NOT NULL,request_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 response LONGBLOB,response_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin,created_at_ms BIGINT NOT NULL,updated_at_ms BIGINT NOT NULL,
 UNIQUE KEY uk_recon_submission_task(task_id),CONSTRAINT fk_recon_submission_task FOREIGN KEY(task_id) REFERENCES b_reconciliation_task(task_id),
 CONSTRAINT ck_recon_submission_state CHECK(state IN ('FROZEN','SENDING','UNKNOWN','ACKNOWLEDGED','REVIEW_REQUIRED')),CONSTRAINT ck_recon_response CHECK((response IS NULL)=(response_hash IS NULL))
);
CREATE TABLE b_refund (
 refund_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,order_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,payment_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 user_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,team_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 amount DECIMAL(10,2) NOT NULL,currency CHAR(3) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 snapshot LONGBLOB NOT NULL,snapshot_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 eligibility_status VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'WAITING_ELIGIBILITY',eligibility_basis VARCHAR(40),eligibility_proof LONGBLOB,eligibility_proof_hash CHAR(64),
 funds_status VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'NONE',version BIGINT NOT NULL DEFAULT 1,created_at_ms BIGINT NOT NULL,updated_at_ms BIGINT NOT NULL,
 UNIQUE KEY uk_refund_order(order_id),UNIQUE KEY uk_refund_payment(payment_id),UNIQUE KEY uk_refund_binding(refund_id,payment_id,order_id),
 CONSTRAINT fk_refund_order FOREIGN KEY(order_id) REFERENCES b_market_order(order_id),CONSTRAINT fk_refund_payment FOREIGN KEY(payment_id) REFERENCES b_payment(payment_id),
 CONSTRAINT ck_refund_eligibility CHECK(eligibility_status IN ('WAITING_ELIGIBILITY','ELIGIBLE','REVIEW_REQUIRED')),
 CONSTRAINT ck_refund_funds CHECK(funds_status='NONE'),CONSTRAINT ck_refund_amount CHECK(amount>0 AND currency='CNY' AND version>0),CONSTRAINT ck_refund_proof CHECK((eligibility_proof IS NULL)=(eligibility_proof_hash IS NULL))
);
CREATE TABLE b_trade_evidence_link (
 work_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,inbox_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 evidence_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,created_at_ms BIGINT NOT NULL,
 PRIMARY KEY(work_id,inbox_id),CONSTRAINT fk_trade_link_work FOREIGN KEY(work_id) REFERENCES b_trade_work(work_id),CONSTRAINT fk_trade_link_inbox FOREIGN KEY(inbox_id) REFERENCES b_trade_inbox(inbox_id)
);
CREATE TABLE b_order_block (
 order_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,kind VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,owner_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 owner_version BIGINT NOT NULL,state VARCHAR(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'ACTIVE',reason VARCHAR(64) NOT NULL,created_at_ms BIGINT NOT NULL,updated_at_ms BIGINT NOT NULL,
 PRIMARY KEY(order_id,kind,owner_id),CONSTRAINT fk_order_block_order FOREIGN KEY(order_id) REFERENCES b_market_order(order_id),CONSTRAINT ck_order_block_kind CHECK(kind IN ('RECONCILIATION','EVIDENCE_CONFLICT','LEGACY_REVIEW')),
 CONSTRAINT ck_order_block_state CHECK(state IN ('ACTIVE','CLEARED') AND owner_version>0),INDEX idx_order_block_active(order_id,state,kind)
);
