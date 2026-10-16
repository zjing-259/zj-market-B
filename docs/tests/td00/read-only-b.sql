-- Whole fresh schema belongs to this run. Later acceptance scopes by fixture goods/order IDs.
START TRANSACTION READ ONLY;
SELECT business_status,COUNT(*) AS orders FROM b_market_order GROUP BY business_status;
SELECT COUNT(*) AS confirmations FROM b_purchase_confirmation;
SELECT SUM(available) AS available,SUM(reserved) AS reserved,SUM(sold) AS sold FROM b_inventory_account;
SELECT state,COUNT(*) AS reservations FROM b_inventory_reservation GROUP BY state;
SELECT kind,COUNT(*) AS ledger_rows FROM b_inventory_ledger GROUP BY kind;
SELECT funds_state,COUNT(*) AS payments,COALESCE(SUM(amount),0) AS amount FROM b_payment GROUP BY funds_state;
SELECT a.state,COUNT(*) AS channel_attempts,COALESCE(SUM(p.amount),0) AS amount
 FROM b_sim_attempt a JOIN b_sim_payment p ON p.payment_id=a.payment_id GROUP BY a.state;
SELECT COUNT(*) AS purchase_guards FROM b_purchase_guard;
SELECT COUNT(*) AS trade_outbox_records FROM b_trade_outbox;
SELECT COUNT(*) AS refund_roots FROM b_refund;
SELECT COUNT(*) AS fulfillments FROM b_fulfillment;
COMMIT;
