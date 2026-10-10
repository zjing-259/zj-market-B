ALTER TABLE b_inventory_operation ADD COLUMN request_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL;
UPDATE b_inventory_operation SET request_hash=SHA2(CONCAT_WS(CHAR(10),operator_id,kind,goods_id,CAST(delta AS CHAR),CAST(expected_version AS CHAR),reason),256);
ALTER TABLE b_inventory_operation MODIFY COLUMN request_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL;
ALTER TABLE b_inventory_operation ADD CONSTRAINT chk_inventory_request_hash CHECK(request_hash REGEXP '^[0-9a-f]{64}$');
