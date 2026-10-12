-- Empty-schema DDL only. No DROP, USE, historical data or repeated phase-one ADD COLUMN.
CREATE TABLE `crowd_tags` (
                              `id` int(11) unsigned NOT NULL AUTO_INCREMENT COMMENT '自增ID',
                              `tag_id` varchar(32) NOT NULL COMMENT '人群ID',
                              `tag_name` varchar(64) NOT NULL COMMENT '人群名称',
                              `tag_desc` varchar(256) NOT NULL COMMENT '人群描述',
                              `statistics` int(8) NOT NULL COMMENT '人群标签统计量',
                              `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                              `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                              PRIMARY KEY (`id`),
                              UNIQUE KEY `uq_tag_id` (`tag_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='人群标签';
CREATE TABLE `crowd_tags_detail` (
                                     `id` int(11) unsigned NOT NULL AUTO_INCREMENT COMMENT '自增ID',
                                     `tag_id` varchar(32) NOT NULL COMMENT '人群ID',
                                     `user_id` varchar(16) NOT NULL COMMENT '用户ID',
                                     `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                                     `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                                     PRIMARY KEY (`id`),
                                     UNIQUE KEY `uq_tag_user` (`tag_id`,`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='人群标签明细';
CREATE TABLE `crowd_tags_job` (
                                  `id` int(11) unsigned NOT NULL AUTO_INCREMENT COMMENT '自增ID',
                                  `tag_id` varchar(32) NOT NULL COMMENT '标签ID',
                                  `batch_id` varchar(8) NOT NULL COMMENT '批次ID',
                                  `tag_type` tinyint(1) NOT NULL DEFAULT '1' COMMENT '标签类型（参与量、消费金额）',
                                  `tag_rule` varchar(8) NOT NULL COMMENT '标签规则（限定类型 N次）',
                                  `stat_start_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '统计数据，开始时间',
                                  `stat_end_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '统计数据，结束时间',
                                  `status` tinyint(1) NOT NULL DEFAULT '0' COMMENT '状态；0初始、1计划（进入执行阶段）、2重置、3完成',
                                  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                                  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                                  PRIMARY KEY (`id`),
                                  UNIQUE KEY `uq_batch_id` (`batch_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='人群标签任务';
CREATE TABLE `group_buy_activity` (
                                      `id` bigint(11) unsigned NOT NULL AUTO_INCREMENT COMMENT '自增',
                                      `activity_id` bigint(8) NOT NULL COMMENT '活动ID',
                                      `activity_name` varchar(128) NOT NULL COMMENT '活动名称',
                                      `discount_id` varchar(8) NOT NULL COMMENT '折扣ID',
                                      `group_type` tinyint(1) NOT NULL DEFAULT '0' COMMENT '拼团方式（0自动成团、1达成目标拼团）',
                                      `take_limit_count` int(4) NOT NULL DEFAULT '1' COMMENT '拼团次数限制',
                                      `target` int(5) NOT NULL DEFAULT '1' COMMENT '拼团目标',
                                      `valid_time` int(4) NOT NULL DEFAULT '15' COMMENT '拼团时长（分钟）',
                                      `status` tinyint(1) NOT NULL DEFAULT '0' COMMENT '活动状态（0创建、1生效、2过期、3废弃）',
                                      `start_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '活动开始时间',
                                      `end_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '活动结束时间',
                                      `tag_id` varchar(32) DEFAULT NULL COMMENT '人群标签规则标识',
                                      `tag_scope` varchar(4) DEFAULT NULL COMMENT '人群标签规则范围（多选；1可见限制、2参与限制）',
                                      `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                                      `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                                      PRIMARY KEY (`id`),
                                      UNIQUE KEY `uq_activity_id` (`activity_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='拼团活动';
CREATE TABLE `group_buy_discount` (
                                      `id` bigint(11) unsigned NOT NULL AUTO_INCREMENT COMMENT '自增ID',
                                      `discount_id` varchar(8) NOT NULL COMMENT '折扣ID',
                                      `discount_name` varchar(64) NOT NULL COMMENT '折扣标题',
                                      `discount_desc` varchar(256) NOT NULL COMMENT '折扣描述',
                                      `discount_type` tinyint(1) NOT NULL DEFAULT '0' COMMENT '折扣类型（0:base、1:tag）',
                                      `market_plan` varchar(4) NOT NULL DEFAULT 'ZJ' COMMENT '营销优惠计划（ZJ:直减、MJ:满减、ZK:折扣、N元购）',
                                      `market_expr` varchar(32) NOT NULL COMMENT '营销优惠表达式',
                                      `tag_id` varchar(32) DEFAULT NULL COMMENT '人群标签，特定优惠限定',
                                      `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                                      `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                                      PRIMARY KEY (`id`),
                                      UNIQUE KEY `uq_discount_id` (`discount_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE `group_buy_order` (
                                   `id` int(11) unsigned NOT NULL AUTO_INCREMENT COMMENT '自增ID',
                                   `team_id` varchar(8) NOT NULL COMMENT '拼单组队ID',
                                   `activity_id` bigint(8) NOT NULL COMMENT '活动ID',
                                   `source` varchar(8) NOT NULL COMMENT '渠道',
                                   `channel` varchar(8) NOT NULL COMMENT '来源',
                                   `original_price` decimal(8,2) NOT NULL COMMENT '原始价格',
                                   `deduction_price` decimal(8,2) NOT NULL COMMENT '折扣金额',
                                   `pay_price` decimal(8,2) NOT NULL COMMENT '支付价格',
                                   `target_count` int(5) NOT NULL COMMENT '目标数量',
                                   `complete_count` int(5) NOT NULL COMMENT '完成数量',
                                   `lock_count` int(5) NOT NULL COMMENT '锁单数量',
                                   `status` tinyint(1) NOT NULL DEFAULT '0' COMMENT '状态（0-拼单中、1-完成、2-失败）',
                                   `valid_start_time` datetime NOT NULL COMMENT '拼团开始时间',
                                   `valid_end_time` datetime NOT NULL COMMENT '拼团结束时间',
                                   `notify_url` varchar(512) NOT NULL COMMENT '回调地址',
                                   `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                                   `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                                   PRIMARY KEY (`id`),
                                   UNIQUE KEY `uq_team_id` (`team_id`),
                                   `goods_id` varchar(16) DEFAULT NULL COMMENT 'Team SKU; legacy NULL is not joinable'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE `group_buy_order_list` (
                                        `id` int(11) unsigned NOT NULL AUTO_INCREMENT COMMENT '自增ID',
                                        `user_id` varchar(64) NOT NULL COMMENT '用户ID',
                                        `team_id` varchar(8) NOT NULL COMMENT '拼单组队ID',
                                        `order_id` varchar(12) NOT NULL COMMENT '订单ID',
                                        `activity_id` bigint(8) NOT NULL COMMENT '活动ID',
                                        `start_time` datetime NOT NULL COMMENT '活动开始时间',
                                        `end_time` datetime NOT NULL COMMENT '活动结束时间',
                                        `goods_id` varchar(16) NOT NULL COMMENT '商品ID',
                                        `source` varchar(8) NOT NULL COMMENT '渠道',
                                        `channel` varchar(8) NOT NULL COMMENT '来源',
                                        `original_price` decimal(8,2) NOT NULL COMMENT '原始价格',
                                        `deduction_price` decimal(8,2) NOT NULL COMMENT '折扣金额',
                                        `status` tinyint(1) NOT NULL DEFAULT '0' COMMENT '状态；0初始锁定、1消费完成、2用户退单',
                                        `out_trade_no` varchar(12) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NOT NULL COMMENT '外部交易单号-确保外部调用唯一幂等',
                                        `out_trade_time` datetime(3) DEFAULT NULL COMMENT '外部交易时间',
                                        `biz_id` varchar(64) NOT NULL COMMENT '业务唯一ID',
                                        `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                                        `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                                        PRIMARY KEY (`id`),
                                        UNIQUE KEY `uq_order_id` (`order_id`),
                                        KEY `idx_user_id_activity_id` (`user_id`,`activity_id`),
                                        `pay_price` decimal(8,2) DEFAULT NULL,
                                        `request_team_id` varchar(8) DEFAULT NULL,
                                        `notify_url` varchar(512) DEFAULT NULL,
                                        UNIQUE KEY `uq_sc_out_trade` (`source`,`channel`,`out_trade_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE `notify_task` (
                               `id` int(11) unsigned NOT NULL AUTO_INCREMENT COMMENT '自增ID',
                               `activity_id` bigint(8) NOT NULL COMMENT '活动ID',
                               `team_id` varchar(8) NOT NULL COMMENT '拼单组队ID',
                               `notify_url` varchar(512) NOT NULL COMMENT '回调接口',
                               `notify_count` int(8) NOT NULL COMMENT '回调次数',
                               `notify_status` tinyint(1) NOT NULL COMMENT '回调状态【0初始、1完成、2重试、3失败、4处理中】',
                               `parameter_json` varchar(256) NOT NULL COMMENT '参数对象',
                               `claim_token` varchar(36) DEFAULT NULL,
                               `lease_until` datetime(3) DEFAULT NULL,
                               `next_attempt_time` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
                               `last_error` varchar(256) DEFAULT NULL,
                               `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                               `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                               PRIMARY KEY (`id`),
                               UNIQUE KEY `uq_team_id` (`team_id`),
                               KEY `idx_notify_due` (`notify_status`, `next_attempt_time`, `id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE `sc_sku_activity` (
                                   `id` int(11) unsigned NOT NULL AUTO_INCREMENT COMMENT '自增ID',
                                   `source` varchar(8) NOT NULL COMMENT '渠道',
                                   `channel` varchar(8) NOT NULL COMMENT '来源',
                                   `activity_id` bigint(8) NOT NULL COMMENT '活动ID',
                                   `goods_id` varchar(16) NOT NULL COMMENT '商品ID',
                                   `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                                   `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                                   PRIMARY KEY (`id`),
                                   UNIQUE KEY `uq_sc_goodsid` (`source`,`channel`,`goods_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='渠道商品活动配置关联表';
CREATE TABLE `sku` (
                       `id` int(11) unsigned NOT NULL AUTO_INCREMENT COMMENT '自增ID',
                       `source` varchar(8) NOT NULL COMMENT '渠道',
                       `channel` varchar(8) NOT NULL COMMENT '来源',
                       `goods_id` varchar(16) NOT NULL COMMENT '商品ID',
                       `goods_name` varchar(128) NOT NULL COMMENT '商品名称',
                       `original_price` decimal(10,2) NOT NULL COMMENT '商品价格',
                       `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                       `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                       PRIMARY KEY (`id`),
                       UNIQUE KEY `uq_goods_id` (`goods_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品信息';
CREATE TABLE IF NOT EXISTS trade_request_guard (
    source VARCHAR(8) NOT NULL,
    channel VARCHAR(8) NOT NULL,
    out_trade_no VARCHAR(12) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NOT NULL,
    PRIMARY KEY (source, channel, out_trade_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS trade_quota_guard (
    user_id VARCHAR(64) NOT NULL,
    activity_id BIGINT NOT NULL,
    PRIMARY KEY (user_id, activity_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
-- Requires MySQL 8 with utf8mb4_0900_bin (verified on 8.0.32).
-- Apply after 20260926-phase1.sql, with old application writers stopped.
-- Preserve the original external ID exactly. 0900_bin is binary and NO PAD.
-- Preflight: audit exact duplicate (source, channel, out_trade_no COLLATE utf8mb4_0900_bin) keys.
ALTER TABLE group_buy_order_list
    MODIFY COLUMN out_trade_no VARCHAR(12) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NOT NULL COMMENT 'Exact external transaction ID',
    MODIFY COLUMN out_trade_time DATETIME(3) NULL DEFAULT NULL COMMENT 'Payment fact with millisecond precision';

ALTER TABLE trade_request_guard
    MODIFY COLUMN out_trade_no VARCHAR(12) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NOT NULL;

ALTER TABLE notify_task
    MODIFY COLUMN notify_url VARCHAR(512) NOT NULL COMMENT 'Callback URL; same limit as accepted lock requests';

-- Existing values are preserved. Lost historical milliseconds cannot be reconstructed.

-- Apply once to each schema after phase-one migrations, before starting the new application.
-- Existing success/failure states and counts are preserved; terminal legacy tasks need manual review.
ALTER TABLE notify_task MODIFY COLUMN notify_status tinyint(1) NOT NULL COMMENT '0 pending, 1 delivered, 2 retry, 3 exhausted, 4 processing';

-- Apply once to the A database before enabling the v2 Dubbo and RocketMQ adapters.
-- Existing facts remain unchanged; only the shared activity mapping and tag member ID capacity grow.
ALTER TABLE sc_sku_activity MODIFY goods_id varchar(64) NOT NULL;
ALTER TABLE crowd_tags_detail MODIFY user_id varchar(64) NOT NULL;
CREATE TABLE IF NOT EXISTS ab_product_projection (
  source varchar(8) COLLATE utf8mb4_0900_bin NOT NULL, channel varchar(8) COLLATE utf8mb4_0900_bin NOT NULL,
  goods_id varchar(64) COLLATE utf8mb4_0900_bin NOT NULL,
  product_version bigint unsigned NOT NULL, goods_name varchar(128) NOT NULL,
  original_price decimal(8,2) NOT NULL, currency char(3) NOT NULL,
  sale_status varchar(16) NOT NULL, content_hash char(64) NOT NULL,
  updated_at datetime(3) NOT NULL,
  PRIMARY KEY(source,channel,goods_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ab_team (
  team_id varchar(64) COLLATE utf8mb4_0900_bin NOT NULL,
  source varchar(8) COLLATE utf8mb4_0900_bin NOT NULL, channel varchar(8) COLLATE utf8mb4_0900_bin NOT NULL,
  activity_id bigint NOT NULL, goods_id varchar(64) COLLATE utf8mb4_0900_bin NOT NULL,
  target_count int NOT NULL, reserved_count int NOT NULL, paid_count int NOT NULL,
  team_status varchar(24) NOT NULL, team_version bigint unsigned NOT NULL,
  valid_start_time datetime(3) NOT NULL, valid_end_time datetime(3) NOT NULL,
  reconciliation_id varchar(64) COLLATE utf8mb4_0900_bin DEFAULT NULL,
  roster_version varchar(64) DEFAULT NULL, roster_json text DEFAULT NULL,
  completion_id varchar(64) COLLATE utf8mb4_0900_bin DEFAULT NULL,
  completion_hash char(64) DEFAULT NULL, resolved_at datetime(3) DEFAULT NULL,
  PRIMARY KEY(team_id), KEY idx_channel_state_end(source,channel,team_status,valid_end_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ab_trade_order (
  source varchar(8) COLLATE utf8mb4_0900_bin NOT NULL, channel varchar(8) COLLATE utf8mb4_0900_bin NOT NULL,
  out_trade_no varchar(64) COLLATE utf8mb4_0900_bin NOT NULL,
  record_kind varchar(16) NOT NULL, order_id varchar(64) COLLATE utf8mb4_0900_bin DEFAULT NULL,
  user_id varchar(64) COLLATE utf8mb4_0900_bin NOT NULL,
  goods_id varchar(64) COLLATE utf8mb4_0900_bin DEFAULT NULL,
  activity_id bigint DEFAULT NULL, product_version bigint unsigned DEFAULT NULL,
  quantity int DEFAULT NULL, request_team_id varchar(64) COLLATE utf8mb4_0900_bin DEFAULT NULL,
  team_id varchar(64) COLLATE utf8mb4_0900_bin DEFAULT NULL,
  original_price decimal(8,2) DEFAULT NULL, deduction_price decimal(8,2) DEFAULT NULL,
  pay_price decimal(8,2) DEFAULT NULL, currency char(3) DEFAULT NULL,
  reserved_at datetime(3) DEFAULT NULL, payment_deadline datetime(3) DEFAULT NULL,
  order_status varchar(16) NOT NULL, record_version bigint unsigned NOT NULL,
  payment_id varchar(64) COLLATE utf8mb4_0900_bin DEFAULT NULL,
  paid_amount decimal(8,2) DEFAULT NULL, paid_at datetime(3) DEFAULT NULL,
  close_id varchar(64) COLLATE utf8mb4_0900_bin DEFAULT NULL,
  close_hash char(64) DEFAULT NULL, closed_at datetime(3) DEFAULT NULL,
  refund_id varchar(64) COLLATE utf8mb4_0900_bin DEFAULT NULL,
  refund_status varchar(16) DEFAULT NULL, refund_version bigint unsigned DEFAULT NULL,
  refund_amount decimal(8,2) DEFAULT NULL, refund_hash char(64) DEFAULT NULL,
  PRIMARY KEY(source,channel,out_trade_no), UNIQUE KEY uq_ab_order_id(order_id),
  KEY idx_ab_team(team_id), KEY idx_ab_user_activity(user_id,activity_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ab_payment_guard (
  source varchar(8) COLLATE utf8mb4_0900_bin NOT NULL, channel varchar(8) COLLATE utf8mb4_0900_bin NOT NULL,
  payment_id varchar(64) COLLATE utf8mb4_0900_bin NOT NULL,
  out_trade_no varchar(64) COLLATE utf8mb4_0900_bin NOT NULL,
  PRIMARY KEY(source,channel,payment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ab_trade_guard (
  source varchar(8) COLLATE utf8mb4_0900_bin NOT NULL,
  channel varchar(8) COLLATE utf8mb4_0900_bin NOT NULL,
  out_trade_no varchar(64) COLLATE utf8mb4_0900_bin NOT NULL,
  PRIMARY KEY(source,channel,out_trade_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ab_inbox (
  consumer varchar(32) NOT NULL, producer varchar(64) COLLATE utf8mb4_0900_bin NOT NULL,
  event_id varchar(64) COLLATE utf8mb4_0900_bin NOT NULL,
  source varchar(8) COLLATE utf8mb4_0900_bin NOT NULL, channel varchar(8) COLLATE utf8mb4_0900_bin NOT NULL,
  event_type varchar(48) NOT NULL, body_hash char(64) NOT NULL,
  processing_status varchar(24) NOT NULL, outcome varchar(16) DEFAULT NULL,
  result_code varchar(64) DEFAULT NULL, result_info varchar(256) DEFAULT NULL,
  result_json text DEFAULT NULL, processed_at datetime(3) DEFAULT NULL,
  created_at datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY(consumer,producer,event_id), KEY idx_ab_inbox_event(event_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ab_outbox (
  event_id varchar(64) COLLATE utf8mb4_0900_bin NOT NULL,
  topic varchar(64) NOT NULL, event_type varchar(48) NOT NULL,
  source varchar(8) COLLATE utf8mb4_0900_bin NOT NULL, channel varchar(8) COLLATE utf8mb4_0900_bin NOT NULL,
  body mediumtext NOT NULL, body_hash char(64) NOT NULL,
  status varchar(16) NOT NULL DEFAULT 'PENDING', attempts int NOT NULL DEFAULT 0,
  next_attempt_at datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  claim_token varchar(64) DEFAULT NULL, lease_until datetime(3) DEFAULT NULL,
  last_error varchar(256) DEFAULT NULL,
  created_at datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  published_at datetime(3) DEFAULT NULL,
  PRIMARY KEY(event_id), KEY idx_ab_outbox_due(status,next_attempt_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ab_waiting_dependency (
  event_id varchar(64) COLLATE utf8mb4_0900_bin NOT NULL,
  consumer varchar(32) NOT NULL, producer varchar(64) NOT NULL,
  body mediumtext NOT NULL, body_hash char(64) NOT NULL,
  next_check_at datetime(3) NOT NULL, attempts int NOT NULL DEFAULT 0,
  PRIMARY KEY(consumer,producer,event_id), KEY idx_ab_waiting_due(next_check_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ab_quarantine (
  id bigint unsigned NOT NULL AUTO_INCREMENT,
  event_id varchar(64) COLLATE utf8mb4_0900_bin DEFAULT NULL,
  reason varchar(128) NOT NULL, body_hash char(64) NOT NULL,
  body mediumtext NOT NULL, created_at datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY(id), KEY idx_ab_quarantine_event(event_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ab_exception_payment (
  source varchar(8) COLLATE utf8mb4_0900_bin NOT NULL, channel varchar(8) COLLATE utf8mb4_0900_bin NOT NULL,
  out_trade_no varchar(64) COLLATE utf8mb4_0900_bin NOT NULL,
  payment_id varchar(64) COLLATE utf8mb4_0900_bin NOT NULL,
  paid_amount decimal(8,2) NOT NULL, paid_at datetime(3) NOT NULL,
  refund_id varchar(64) COLLATE utf8mb4_0900_bin DEFAULT NULL,
  PRIMARY KEY(source,channel,out_trade_no), UNIQUE KEY uq_ab_exception_payment(source,channel,payment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

