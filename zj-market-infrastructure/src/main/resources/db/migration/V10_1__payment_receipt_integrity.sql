-- Add the frozen receipt audit without editing already-applied V10 or historical migrations.
ALTER TABLE b_payment_operation ADD receipt_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL;
UPDATE b_payment_operation SET receipt_hash=SHA2(CAST(receipt_json AS CHAR),256);
ALTER TABLE b_payment_operation MODIFY receipt_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL;
