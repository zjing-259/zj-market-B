-- Original wire bytes are LONGBLOB: JSON normalization must not change HMAC/body hashes.
CREATE TABLE b_trade_outbox (
 event_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 payment_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 order_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 event_type VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 fact_version BIGINT NOT NULL DEFAULT 1, body LONGBLOB NOT NULL, body_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 state VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'READY',
 next_attempt_ms BIGINT NOT NULL, lease_token VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,lease_until_ms BIGINT,
 failure_count INT NOT NULL DEFAULT 0, alerted BOOLEAN NOT NULL DEFAULT FALSE,last_error VARCHAR(64),created_at_ms BIGINT NOT NULL,
 UNIQUE KEY uk_trade_fact(payment_id,event_type,fact_version),FOREIGN KEY(payment_id) REFERENCES b_payment(payment_id),FOREIGN KEY(order_id) REFERENCES b_market_order(order_id),
 CHECK(event_type='PAYMENT_SUCCEEDED' AND fact_version=1 AND failure_count>=0),CHECK(state IN ('READY','PUBLISHED','DONE','REVIEW_REQUIRED')),
 CHECK((lease_token IS NULL)=(lease_until_ms IS NULL)),INDEX idx_trade_outbox_due(state,next_attempt_ms,lease_until_ms)
);
CREATE TABLE b_trade_inbox (
 inbox_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,consumer_business VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'TRADE',
 producer VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,event_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,event_type VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 body LONGBLOB NOT NULL,body_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, original_event_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 state VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'READY',next_attempt_ms BIGINT NOT NULL,created_at_ms BIGINT NOT NULL,last_error VARCHAR(64),
 UNIQUE KEY uk_trade_inbox(consumer_business,producer,event_id),CHECK(state IN ('READY','WAITING_DEPENDENCY','DONE','REVIEW_REQUIRED')),INDEX idx_trade_inbox_due(state,next_attempt_ms)
);
CREATE TABLE b_trade_quarantine (
 quarantine_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,receipt_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,topic VARCHAR(128),tag VARCHAR(64),key_id VARCHAR(128),signature VARCHAR(256),
 body LONGBLOB NOT NULL,body_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,reason VARCHAR(64) NOT NULL,created_at_ms BIGINT NOT NULL,
 UNIQUE KEY uk_trade_quarantine(receipt_key,body_hash,reason)
);
CREATE TABLE b_trade_work (
 work_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,kind VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,business_key VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 order_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,payment_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,team_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 state VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, evidence LONGBLOB NOT NULL,evidence_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 reasons JSON NOT NULL,created_at_ms BIGINT NOT NULL,updated_at_ms BIGINT NOT NULL,next_attempt_ms BIGINT NOT NULL DEFAULT 0,
 lease_token VARCHAR(64),lease_until_ms BIGINT,intent_version BIGINT NOT NULL DEFAULT 1,failure_count INT NOT NULL DEFAULT 0,
 UNIQUE KEY uk_trade_work(kind,business_key),CHECK(state IN ('READY','LEASED','WAITING_DEPENDENCY','DEFERRED_B05','REVIEW_REQUIRED','DONE')),CHECK(intent_version>0 AND failure_count>=0),INDEX idx_trade_work_due(state,next_attempt_ms)
);
CREATE TABLE b_team_cursor (
 source VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,channel VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,team_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 team_version BIGINT NOT NULL,status VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,body LONGBLOB NOT NULL,fact_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,review_required BOOLEAN NOT NULL DEFAULT FALSE,
 PRIMARY KEY(source,channel,team_id),CHECK(team_version>0)
);
ALTER TABLE b_sim_notification ADD COLUMN lease_token VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,ADD COLUMN lease_until_ms BIGINT,ADD COLUMN failure_count INT NOT NULL DEFAULT 0;
ALTER TABLE b_payment ADD COLUMN success_fact LONGBLOB,ADD COLUMN success_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin;
