-- Run only in the explicitly selected TD fixture schema, never use a default DB.
-- These snapshots expose no member/payment identifiers. No lock/state transition.
START TRANSACTION READ ONLY;
SELECT UTC_TIMESTAMP(3) AS server_time;
SELECT team_status, COUNT(*) AS teams, SUM(reserved_count) AS reserved_count,
       SUM(paid_count) AS accepted_paid_count FROM ab_team GROUP BY team_status;
SELECT COUNT(*) AS invalid_counts FROM ab_team
 WHERE paid_count < 0 OR paid_count > reserved_count OR reserved_count > target_count OR target_count > 100;
SELECT record_kind, order_status, COUNT(*) AS records,
       COALESCE(SUM(paid_amount),0) AS accepted_paid_amount
 FROM ab_trade_order GROUP BY record_kind, order_status;
SELECT COUNT(*) AS outbox_records FROM ab_outbox;
SELECT COUNT(*) AS exception_payments FROM ab_exception_payment;
COMMIT;
