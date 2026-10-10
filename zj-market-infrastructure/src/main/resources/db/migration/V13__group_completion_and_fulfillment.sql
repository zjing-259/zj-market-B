-- A completion is a durable per-order obligation; shipping is outside B-04.
CREATE TABLE b_fulfillment (
 order_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 payment_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 user_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 goods_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 team_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 team_version BIGINT NOT NULL,
 status VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'PENDING',
 snapshot LONGBLOB NOT NULL,snapshot_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 confirmed_at_ms BIGINT NOT NULL,version BIGINT NOT NULL DEFAULT 1,
 FOREIGN KEY(order_id,user_id,goods_id) REFERENCES b_market_order(order_id,user_id,goods_id),
 FOREIGN KEY(payment_id) REFERENCES b_payment(payment_id),
 CHECK(status='PENDING'),CHECK(team_version>0 AND version>0),
 INDEX idx_fulfillment_user(user_id,confirmed_at_ms,order_id)
);
ALTER TABLE b_trade_work ADD alerted BOOLEAN NOT NULL DEFAULT FALSE,
 ADD CONSTRAINT ck_completion_lease CHECK((lease_token IS NULL AND lease_until_ms IS NULL) OR (lease_token IS NOT NULL AND lease_until_ms IS NOT NULL));
