> 最新Git状态（2026-10-10）：用户授权后，B-04.0～.6及通知租约P2补修已提交为`1b5242ed1d34722dba52b84a3962e6dc3abb41b2`，已快进合并master；origin/b-04与origin/master首次推送成功，远程核验均为该提交。b-04已关联origin/b-04。本次文档状态记录随随后文档提交同步两分支；下文“未提交/未合并/未推送”均为各次开发验收当时的历史状态。当前工作树仍为D:/Java/zj-market-b-04；B-05/B-06未开展。

> 最新补修（2026-10-10）：通知ACK/重试先锁行再取数据库时间校验租约；六组真实SQL及受影响回归通过，详细过程与新包指纹见[B-04第16节](b04-development.md)。第15节原联合验收为历史批次，B-05/B-06尚未开展。

# B-04 → B-05 到期核对与退款接续

更新：2026-10-10。实际工作树D:/Java/zj-market-b-04，分支b-04，基线7cef241，B-04成果未提交。B-04.6联合验收按模拟范围已完成，最终批次b046-20261010-final-pass，最终状态/失败/产物指纹以[b04-development.md第15节](b04-development.md)和[路线图](development-roadmap.md)为准。本文件是实现交接，不替代[A权威契约](../../group-buy-market/docs/ab-api-contract.md)。B-05尚未实施，禁止把持久接收当退款执行完成。

## 已有能力和接管位置

B-04已实现独立持久模拟渠道、稳定paymentId/多attemptId、可信资金/原支付Outbox/签名结果、全根未付关闭证明、可信完整名单/单订单Trade.query和原子CONFIRM/PENDING。普通checkout/events默认关闭，恢复与新支付开关分离。资金仅模拟；不产生第三方扣款，没有第三方退款、回调或物流验收。

| 持久入口 | 当前含义与B-05接续 |
| --- | --- |
| b_trade_inbox | 保存原字节body/hash、producer/eventId/type/originalEventId；TEAM_FAILED/RECONCILIATION可信接收与拆工作同事务后ACK。Inbox DONE只代表该消息已承担，不能据此宣称退款/核对完成 |
| b_trade_work TEAM_RECONCILIATION_REQUIRED | 完整团队事件按名单逐单工作；DEFERRED_B05或缺本地订单WAITING_DEPENDENCY。Trade.query补偿也可能产生单订单工作，证据类型不同，不能伪装完整名单 |
| b_trade_work TEAM_FAILED | 原完整outTradeNoList、refundRequiredOutTradeNoList、reconciliationId/reason等保留在evidence中；逐单持久交接，不直接释放未付或已付库存 |
| b_trade_work REFUND_OBLIGATION | paymentId:orderId唯一business_key，窗口外资金、A拒绝、团队失败合并reasons。DEFERRED_B05表示待接管，SUCCEEDED资金保持；不存在退款执行成功事实 |
| b_team_cursor / b_trade_quarantine | 作用域团队最新版本/原正文/规范事实hash；同版本异名单、终局矛盾等留档核对，不能仅提高版本就倒退已履约事实 |
| b_payment / b_sim_payment / b_sim_attempt | 商城成功事实与独立渠道原成功、paidAt、冻结金额/窗口；UNKNOWN必须查原payment/attempt，不换键收第二笔 |
| b_fulfillment / reservation / ledger / guard | 已完成团队CONFIRMED/唯一CONFIRM/PENDING；尚未核对/退款HELD并占guard。B-05退款后释放路径不得复用CLOSED_UNPAID或回滚sold冒充未付取消 |

源码入口：SettlementRepository.receive/stageTeam/applyInbox/applyTeamOrder；TradeMessageReader验签/严格消息结构；RocketMqSettlementTransport原事件/完整Trade.query；PaymentClosingRepository原关闭隔离；FulfillmentRepository原成团恢复。消息消费者复用现有独立交易组，不新建另一组重新消费全量团队事件。

## 工作证据、去重与恢复约束

V11 work列为work_id/kind/business_key/order_id/payment_id/team_id/state/evidence/evidence_hash/reasons/created_at_ms/updated_at_ms/next_attempt_ms/lease_token/lease_until_ms/intent_version/failure_count，V13加alerted及租约成对约束。没有独立team_version、reconciliation_id或roster_version列，这些在原JSON evidence内。团队business_key按source/channel/team/version/order的SHA256；退款义务按paymentId:orderId。缺本地订单没有FK拒收；不得猜用户查询A，待明确归属再补查。

evidence是LONGBLOB原字节，hash是原字节SHA256；cursor.fact_hash则是规范ContractCodec的{type,payload}摘要，两者不可混用。JSON只读查询先CONVERT(evidence USING utf8mb4)。同业务工作重复接收保留第一份evidence/hash，合并reasons并必要时增intent_version；后续各原消息仍在Inbox/quarantine中，B-05需要按订单/payment/team关联追溯完整来源，不能把第一份证据当所有原因的完整证据。重复事件不同eventId不新增业务义务；同eventId异正文隔离。

DEFERRED_B05目前没有执行扫描器。WAITING_DEPENDENCY由现有资金接收补依赖，但不会执行退款/核对。B-05需要显式领取其工作，锁后读数据库时间核对intent/token/lease，过期令牌不可提交；故障告警不终止原键恢复。网络/模拟端口调用在商城事务外。所有新执行必须遵循已有user→product→guard→inventory account→order→reservation→trade coordination→payment→attempts→operations→task，再Outbox/团队游标/对应work/fulfillment的锁序；退款执行表增加后统一定义位置并检查反向锁，不能先锁work再回锁业务链。

## B-05必须实现的顺序与安全门槛

1. 核对到期完整名单：可信原reconciliationId/rosterVersion和A当前团队状态/完整名单，逐个补查本单Trade.query及原渠道支付事实。团队查询不能独自证明本单资金；局部名单、缺订单、未决attempt、未知资金或矛盾继续可见等待/人工核对，不能凭MQ保留期或超时自动判未付。
2. 通过既有TeamService.queryReconciliation取得冻结名单/版本，再用TeamService.completeReconciliation RPC提交精确完整结果；持久化稳定completionId/不可变原请求，TLS签名调用在本地事务外，响应丢失用原请求/权威查询恢复，不新造核对MQ事件类型。支付的Broker ACK不代表A接受，PAID_ACCEPTED需原paymentId及A支付证据；CLOSED_UNPAID需已CANCELLED及原closeId；PAID_OUTSIDE_WINDOW需原paymentId/paidAt/paidAmount/CNY/已持久refundId。UNKNOWN/缺成员/冲突不得提交伪造完整名单，不凭到期判失败，不改写历史paidAt、原支付event、冻结订单/关闭证明。
3. 模拟全额退款端口：原成功payment/渠道流水、服务端稳定refundId/不可变请求hash，独立渠道事务持久退款事实及通知；未知查原键，明确失败才按确定语义重试。同payment累计成功退款不超原成功金额；不能提供普通用户“退款成功”按钮。
4. 商城可信退款事实与REFUND_STATUS_CHANGED Outbox同事务；扩展独立交易结果验证/查询，不放宽商品reader。只有可信全额退款及A所需终局证据齐备，HELD→RELEASED、reserved→available、唯一RELEASE/退款关联、订单终态、清本单guard与work完成才原子提交。失败/UNKNOWN保留HELD/guard，不能伪造CLOSED_UNPAID。
5. 补运营可见状态、分页异常/退避告警、受控CHECK/重试。旧交易任务PAUSE/RESUME/CHECK不能越过资金裁决或直接释放；已PENDING/CONFIRMED遭终局矛盾先隔离，具体逆向履约另设计。

A契约8.4已要求订单/支付绑定稳定refundId，失败重试仍使用该退款业务标识，渠道尝试编号由B内部管理，不再作为待选问题。A允许最终失败/完整核对后先释放库存；本项目沿用已确认B03-D11～D13更严格规则，须全额退款成功且释放完成后解除guard。退款调用不等待A退款回执；A暂不可用时持久同步工作，不能阻止已确认的退款执行。A对迟到付款退款及超窗支付的证据要求必须实现，不能把没有普通PAYMENT_SUCCEEDED Outbox的退款义务漏掉。

B-05的新迁移从V14开始，旧V1～V13（含V10.1）保持；runtime目前精确35表DML，无DDL/history/A/system/grant。迁移/账号变更由verification工具执行，普通包不含Flyway或故障入口。

A的退款消息仅接受PENDING/FAILED/SUCCEEDED及单调refundVersion，渠道UNKNOWN只属于内部未决结果，不能发送UNKNOWN或伪报FAILED/SUCCEEDED；A结果要求outTradeNo/refundId/refundStatus/refundVersion/recordVersion严格匹配。核对请求的completionId与退款业务refundId分别稳定，二者不能混用。

尚需B-05实施时逐项确认：退款明确失败的业务重试模型/渠道退款尝试边界、异常运营操作及权限、模拟退款故障注入策略。D1～D7与全额/后台自动退款/UNKNOWN原键核对已经确认，不重复询问；不在B-04.6擅自替用户确定新的退款操作策略。

## B-05验收要求与数据保留

覆盖真实A到期核对、完整名单/缺本地成员/版本缺口、全部付款与部分付款的终局；独立退款提交前后崩溃、响应/通知/ACK丢失、失败/未知重试、同payment多原因唯一义务/不超额、退款与旧支付/关单任务竞争、A/B新进程恢复、退款后唯一RELEASE及新订单guard安全、权限/正常包/旧成功链路回归。

只读接管检查入口：docs/tests/run-b04-handoff.ps1，独立批次target/b04-handoff/<RunName>/snapshot.json。统计累计隔离库work各kind/state、资金/A接受状态、缺本地工作、PENDING及安全约束；不领取工作、不调用渠道/A、不释放、不清库。累计库同时含受控和真实A样本，不能作为生产待退款数或真实A退款验收证明。当前审计以B-04没有退款执行为前提，将成功/UNKNOWN资金的RELEASED列为违规；B-05实现后必须扩展为校验可信全额退款/终局及唯一RELEASE证据，不能永久禁止合法退款后释放。全量库存/名额守恒证据应按每个新验收批次的明确订单集合报告，不能把历史隔离故障样本混作同一真实团队。

所有旧成功/UNKNOWN/异常/失败批次及原始资金/消息/核对义务保留；HELD/guard不得人工删除。新阶段用B新建订单及完整团队，复核A窗口与活动target，禁止拿直接A占位或旧超时订单拼接B闭环。凭据只读被忽略DPAPI/.local，报告不含登录令牌/密钥；A主工作区、B主目录、默认Java8与共享中间件保持。
