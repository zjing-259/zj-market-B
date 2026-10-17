-- TD-01 additive indexes. Apply ONCE with the migration account in the selected A schema.
-- Do not apply to B; no historical migration, table, record or existing index is rewritten.
CREATE INDEX idx_ab_team_discovery ON ab_team
 (source,channel,goods_id,activity_id,team_status,valid_end_time,team_id);
CREATE INDEX idx_ab_order_discovery_owner ON ab_trade_order
 (team_id,user_id,order_status);
