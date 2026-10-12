-- Never rewrite V11's applied migration or rely on auto-generated CHECK ordinals.
ALTER TABLE b_trade_outbox ADD COLUMN refund_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin;
SET @refund_check_count = (SELECT COUNT(*) FROM information_schema.check_constraints WHERE constraint_schema=DATABASE() AND constraint_name IN (SELECT constraint_name FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND table_name='b_trade_outbox' AND constraint_type='CHECK') AND check_clause LIKE '%event_type%' AND check_clause LIKE '%PAYMENT_SUCCEEDED%');
SET @refund_check_name = (SELECT MAX(constraint_name) FROM information_schema.check_constraints WHERE constraint_schema=DATABASE() AND constraint_name IN (SELECT constraint_name FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND table_name='b_trade_outbox' AND constraint_type='CHECK') AND check_clause LIKE '%event_type%' AND check_clause LIKE '%PAYMENT_SUCCEEDED%');
SET @refund_check_ddl = IF(@refund_check_count=1,CONCAT('ALTER TABLE b_trade_outbox DROP CHECK `',REPLACE(@refund_check_name,'`','``'),'`'),'V16_REQUIRES_EXACTLY_ONE_ORIGINAL_PAYMENT_CHECK');
PREPARE refund_check_stmt FROM @refund_check_ddl;
EXECUTE refund_check_stmt;
DEALLOCATE PREPARE refund_check_stmt;
ALTER TABLE b_trade_outbox
 ADD CONSTRAINT ck_trade_fact_kind CHECK(failure_count>=0 AND ((event_type='PAYMENT_SUCCEEDED' AND fact_version=1 AND refund_id IS NULL) OR (event_type='REFUND_STATUS_CHANGED' AND fact_version>0 AND refund_id IS NOT NULL))),
 ADD CONSTRAINT fk_trade_refund_binding FOREIGN KEY(refund_id,payment_id,order_id) REFERENCES b_refund(refund_id,payment_id,order_id);
ALTER TABLE b_refund
 ADD COLUMN sync_status VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'NOT_CREATED',
 ADD COLUMN accepted_version BIGINT NOT NULL DEFAULT 0,
 ADD COLUMN accepted_status VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin,
 ADD COLUMN a_record_version BIGINT NOT NULL DEFAULT 0,
 ADD COLUMN sync_error VARCHAR(64),
 ADD CONSTRAINT ck_refund_sync CHECK(sync_status IN ('NOT_CREATED','PENDING','ACCEPTED','WAITING_DEPENDENCY','REVIEW_REQUIRED') AND accepted_version>=0 AND accepted_version<=fact_version AND a_record_version>=0 AND ((accepted_version=0 AND accepted_status IS NULL) OR (accepted_version>0 AND accepted_status IN ('PENDING','FAILED','SUCCEEDED'))));
-- RPC authority is a typed Trade.query snapshot, never an unsigned MQ message.
ALTER TABLE b_trade_inbox ADD COLUMN authority LONGBLOB, ADD COLUMN authority_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 ADD CONSTRAINT ck_trade_authority CHECK((authority IS NULL)=(authority_hash IS NULL));
