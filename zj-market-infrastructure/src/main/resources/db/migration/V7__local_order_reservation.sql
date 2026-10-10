CREATE TABLE b_purchase_confirmation (
 confirmation_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 user_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 source VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 channel VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 goods_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 product_version BIGINT NOT NULL, activity_id BIGINT NOT NULL,
 mode VARCHAR(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 team_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 snapshot JSON NOT NULL, issued_at_ms BIGINT NOT NULL, expires_at_ms BIGINT NOT NULL, bound_at_ms BIGINT,
 FOREIGN KEY(user_id) REFERENCES b_user(user_id), FOREIGN KEY(goods_id) REFERENCES b_product(goods_id),
 UNIQUE KEY uk_confirmation_owner_goods(confirmation_id,user_id,goods_id),
 CHECK(product_version>0 AND activity_id>0), CHECK(expires_at_ms>issued_at_ms),
 CHECK((mode='OPEN' AND team_id IS NULL) OR (mode='JOIN' AND team_id IS NOT NULL)),
 INDEX idx_confirmation_expiry(expires_at_ms,confirmation_id), INDEX idx_confirmation_user(user_id,issued_at_ms,confirmation_id)
);
CREATE TABLE b_purchase_guard (
 user_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 goods_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 active_order_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 updated_at_ms BIGINT NOT NULL,
 PRIMARY KEY(user_id,goods_id), FOREIGN KEY(user_id) REFERENCES b_user(user_id), FOREIGN KEY(goods_id) REFERENCES b_product(goods_id)
);
CREATE TABLE b_market_order (
 order_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 user_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 source VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 channel VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 purchase_intent_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 request_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 confirmation_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 goods_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 snapshot JSON NOT NULL, reserve_request JSON NOT NULL, reserve_request_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 quantity INT NOT NULL DEFAULT 1, original_price DECIMAL(8,2) NOT NULL, deduction_price DECIMAL(8,2) NOT NULL, pay_price DECIMAL(8,2) NOT NULL,
 currency VARCHAR(3) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 business_status VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 order_version BIGINT NOT NULL DEFAULT 1, created_at_ms BIGINT NOT NULL, updated_at_ms BIGINT NOT NULL,
 reserve_wait_deadline_ms BIGINT NOT NULL, may_have_dispatched BOOLEAN NOT NULL DEFAULT FALSE,
 payment_exposure VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'NEVER_OPENED',
 FOREIGN KEY(user_id) REFERENCES b_user(user_id), FOREIGN KEY(goods_id) REFERENCES b_product(goods_id),
 FOREIGN KEY(confirmation_id,user_id,goods_id) REFERENCES b_purchase_confirmation(confirmation_id,user_id,goods_id),
 UNIQUE KEY uk_order_intent(user_id,source,channel,purchase_intent_id), UNIQUE KEY uk_order_confirmation(confirmation_id),
 UNIQUE KEY uk_order_goods(order_id,goods_id), UNIQUE KEY uk_order_owner_goods(order_id,user_id,goods_id),
 CHECK(quantity=1 AND currency='CNY'), CHECK(original_price>=0.01 AND deduction_price>=0 AND pay_price>=0.01 AND original_price-deduction_price=pay_price),
 CHECK(order_version>0 AND reserve_wait_deadline_ms>created_at_ms),
 CHECK(business_status IN ('PROCESSING','WAITING_PAYMENT','CLOSING','CLOSED')),
 INDEX idx_order_user(user_id,created_at_ms,order_id), INDEX idx_order_due(business_status,reserve_wait_deadline_ms,order_id)
);
ALTER TABLE b_purchase_guard ADD CONSTRAINT fk_guard_order FOREIGN KEY(active_order_id,user_id,goods_id) REFERENCES b_market_order(order_id,user_id,goods_id);
CREATE TABLE b_inventory_reservation (
 order_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 goods_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 quantity INT NOT NULL DEFAULT 1, state VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 created_at_ms BIGINT NOT NULL, resolved_at_ms BIGINT, resolution_basis VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 FOREIGN KEY(order_id,goods_id) REFERENCES b_market_order(order_id,goods_id), FOREIGN KEY(goods_id) REFERENCES b_inventory_account(goods_id),
 CHECK(quantity=1), CHECK(state IN ('HELD','RELEASED','CONFIRMED')),
 CHECK((state='HELD' AND resolved_at_ms IS NULL AND resolution_basis IS NULL) OR (state<>'HELD' AND resolved_at_ms IS NOT NULL AND resolution_basis IS NOT NULL)),
 INDEX idx_reservation_goods(goods_id,state,order_id)
);
CREATE TABLE b_trade_coordination (
 order_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 intent VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, intent_version BIGINT NOT NULL DEFAULT 1,
 run_state VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, paused BOOLEAN NOT NULL DEFAULT FALSE,
 task_version BIGINT NOT NULL DEFAULT 1, next_attempt_ms BIGINT NOT NULL,
 lease_token VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin, lease_until_ms BIGINT,
 attempt_count BIGINT NOT NULL DEFAULT 0, failure_count BIGINT NOT NULL DEFAULT 0, alerted BOOLEAN NOT NULL DEFAULT FALSE,
 last_error VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 FOREIGN KEY(order_id) REFERENCES b_market_order(order_id),
 CHECK(intent IN ('RESERVE','QUERY','CLOSE','NONE')), CHECK(run_state IN ('READY','LEASED','REVIEW_REQUIRED','DONE')),
 CHECK(intent_version>0 AND task_version>0 AND attempt_count>=0 AND failure_count>=0),
 CHECK((lease_token IS NULL AND lease_until_ms IS NULL) OR (lease_token IS NOT NULL AND lease_until_ms IS NOT NULL)),
 INDEX idx_coord_due(run_state,paused,next_attempt_ms,lease_until_ms,order_id)
);
-- Preserve all executed V5/V6 checksums and historical operator ledgers.
ALTER TABLE b_inventory_ledger
 MODIFY operation_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
 ADD order_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
 ADD business_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
 DROP CHECK b_inventory_ledger_chk_1, DROP CHECK b_inventory_ledger_chk_3, DROP CHECK b_inventory_ledger_chk_4;
UPDATE b_inventory_ledger SET business_key=operation_id;
ALTER TABLE b_inventory_ledger MODIFY business_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 ADD CONSTRAINT fk_ledger_order FOREIGN KEY(order_id,goods_id) REFERENCES b_market_order(order_id,goods_id),
 ADD UNIQUE KEY uk_ledger_business(goods_id,kind,business_key),
 ADD CONSTRAINT ck_ledger_parent CHECK((kind IN ('INBOUND','ADJUST') AND operation_id IS NOT NULL AND order_id IS NULL AND business_key=operation_id) OR (kind IN ('RESERVE','RELEASE','CONFIRM') AND operation_id IS NULL AND order_id IS NOT NULL AND business_key=order_id)),
 ADD CONSTRAINT ck_ledger_change CHECK(
 (kind IN ('INBOUND','ADJUST') AND after_available-before_available=delta_available AND delta_available<>0 AND after_reserved=before_reserved AND after_sold=before_sold) OR
 (kind='RESERVE' AND delta_available=-1 AND after_available=before_available-1 AND after_reserved=before_reserved+1 AND after_sold=before_sold) OR
 (kind='RELEASE' AND delta_available=1 AND after_available=before_available+1 AND after_reserved=before_reserved-1 AND after_sold=before_sold) OR
 (kind='CONFIRM' AND delta_available=0 AND after_available=before_available AND after_reserved=before_reserved-1 AND after_sold=before_sold+1));
