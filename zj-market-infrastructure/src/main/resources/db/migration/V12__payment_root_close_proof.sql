-- Additive only: preserve all historical requests and V1..V11 checksums.
ALTER TABLE b_payment
 ADD channel_close_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 ADD channel_close_request LONGBLOB, ADD channel_close_request_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 ADD channel_close_proof LONGBLOB, ADD channel_close_proof_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 ADD covered_attempt_no INT, ADD channel_closed_at_ms BIGINT, ADD close_verified_at_ms BIGINT,
 ADD CONSTRAINT ck_payment_close_request CHECK((channel_close_id IS NULL AND channel_close_request IS NULL AND channel_close_request_hash IS NULL) OR (channel_close_id IS NOT NULL AND channel_close_request IS NOT NULL AND channel_close_request_hash IS NOT NULL)),
 ADD CONSTRAINT ck_payment_close_proof CHECK((channel_close_proof IS NULL AND channel_close_proof_hash IS NULL AND covered_attempt_no IS NULL AND channel_closed_at_ms IS NULL AND close_verified_at_ms IS NULL) OR (channel_close_id IS NOT NULL AND channel_close_proof IS NOT NULL AND channel_close_proof_hash IS NOT NULL AND covered_attempt_no IS NOT NULL AND covered_attempt_no>0 AND channel_closed_at_ms IS NOT NULL AND close_verified_at_ms IS NOT NULL AND close_verified_at_ms>=channel_closed_at_ms));
ALTER TABLE b_sim_payment
 ADD close_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 ADD close_request_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 ADD close_result LONGBLOB, ADD close_result_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin,
 ADD CONSTRAINT ck_sim_root_close CHECK((close_id IS NULL AND close_request_hash IS NULL AND close_result IS NULL AND close_result_hash IS NULL) OR (close_id IS NOT NULL AND close_request_hash IS NOT NULL AND close_result IS NOT NULL AND close_result_hash IS NOT NULL));
ALTER TABLE b_market_order ADD channel_close_proof_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin;
