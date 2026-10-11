> 最新Git归档状态（2026-10-11）：B-05.0～.6支持范围成果已提交为 `3de9404776377f778d5f6930d3c5ae6fd754bf68`，已快进合并master并原子推送；origin/b-05与origin/master已远程核验一致。当前分支b-05已关联origin/b-05。本条及过程归档记录随随后文档提交同步两分支；下文旧HEAD、未提交／未合并／未推送等保留各次实施时点，不代表最新状态。验收摘要中的基线和包指纹保持原始证据；B-06尚未实施。

> 当前状态（2026-10-11）：B-05.6联合故障验收与B-06交接已完成支持范围内验收。最终同包106项JUnit/前端构建、新SQL及跨JVM/浏览器、真实A无人/部分付款停机退款释放/全付款最后事件成团竞争、逐单资金库存及A名额只读核验、原三专项/交接审计/普通启动均通过。推荐D26～D28已写双路线图，证据及边界见[b05-development.md第15.2节](b05-development.md)、[B-06交接](b05-b06-handoff.md)与[持久验收摘要](tests/b05-joint-acceptance.json)。取消后异常收款正向自动资格未开放，隔离验收通过；此限制不宣称全自动闭环。b-05/53ad32d，全部成果未提交/合并/推送，B-06未开展。下文旧阶段状态保留历史时点。

> 当前状态（2026-10-11）：B-05.5库存收尾及运营页面已完成本阶段验收。双B库V18/runtime48表精确DML；最终同包106项JUnit、SQL05及跨JVM、实际B HTTP浏览器04、真实A live02停机退款/释放/新B重放/恢复后同步、原关单/结算/履约回归、只读交接审计及普通启动均通过。推荐D21～D25已写双路线图，详情见[b05-development.md第14.3节](b05-development.md)。最终只读归档target/refund/b055-20261011-delivery-03/report.json；.6完整联合故障矩阵未开展。b-05/53ad32d，全部阶段改动未提交/合并/推送。下文带日期的旧状态保留历史时点。

> 当前状态（2026-10-11）：B-05.4可信退款事实与A同步已实现并通过同包业务验收；b-05/53ad32d，阶段变更未提交/合并/推送。双B库V16/runtime46表精确DML；103项JUnit、SQL03/跨JVM、实际A live-02停启/签名MQ/严格查询/新B进程、关单/结算/履约回归及普通启动通过。推荐D18～D20已保存双路线图；最终归档见target/refund/b054-20261011-delivery-02/report.json，过程见[b05-development.md第13.2节](b05-development.md)。付费HELD/guard保留；库存释放/HTTP/页面归.5、完整联合矩阵归.6。A外部并行改动保持，实际验收A包及契约不变。下列旧状态保留历史时点。

> 当前状态（2026-10-11）：B-05.3独立模拟退款已完成并验收通过；b-05/53ad32d，全部阶段变更未提交/合并/推送。双B库V15、runtime46表精确DML；99项JUnit、同包SQL/跨JVM、真实A完整核对资格及自有A停止后独立退款、关单/结算/履约回归和普通包默认启动通过。新增推荐D15～D17已保存双路线图。最终报告target/refund/b053-20261011-delivery-02/report.json；详见[B-05过程12.2](b05-development.md)。退款MQ/库存释放/运营及页面归.4/.5，.4～.6未开展；下列旧状态保留历史时点。

> 当前状态（2026-10-11）：B-05.2到期完整核对已完成并验收通过；工作树D:/Java/zj-market-b-05，分支b-05/53ad32d，改动未提交/合并/推送。双B库V14、41表精确DML；87项JUnit、最终同包真实A成团竞争/部分付款丢响应跨JVM恢复、SQL及关单/结算/履约回归通过。最终报告target/reconciliation/b052-20261011-delivery-03/report.json；详见[B-05过程11.4](b05-development.md)。退款义务已持久化，资金仍NONE、付费HELD保留；退款执行归.3，.3～.6未开展。下列暂停及旧阶段记录保留历史时点，以本条和11.4为当前状态。

> 当前状态（2026-10-11）：用户明确要求暂停B-05.2，等待用户明天说“恢复工作”后继续。.2尚未完成，不自动推进.3。代码和双库V14/41表保留，87项JUnit及最终SQL批次07、真实A部分付款批次live-02已通过；成团竞争批次completed-01由用户暂停中断，尚无通过结论，受影响专项回归及最终文档收口待做。工作树D:/Java/zj-market-b-05、分支b-05/53ad32d；未提交/合并/推送。完整恢复清单见[B-05过程11.3](b05-development.md)。

> B-05接续更新（2026-10-10）：.0基线和.1联合设计已完成，D1～D3已确认、D4～D11已按用户授权推荐选择并写入[路线图23.2](development-roadmap.md)。设计/接口/迁移/故障矩阵见[b05-joint-design.md](b05-joint-design.md)，唯一过程见[B-05第10节](b05-development.md)。本交接下文保留B-04归档时点；核对/退款执行器仍未实现、当前V13/35表，旧UNKNOWN/HELD/guard及原始证据保持。

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


## B-05.3已接续与后续边界（2026-10-11）

独立模拟全额退款、退款尝试/查单/通知/持续恢复已落地；原稳定payment/refund绑定、原paidAt/资金/Outbox不改，UNKNOWN只查原attempt、FAILED才新尝试，累计成功不超原金额。D15～D17及真实故障证据见B-05过程12.2/路线图23.11。当前V15/46表；已退款资金保存单调版本事实，但未发送REFUND_STATUS_CHANGED或完成库存收尾。B-05.4须追补全部冻结版本Outbox并严格验证回执；B-05.5须凭可信全额退款/不履约证明原子RELEASE并只清原guard。当前旧B04只读接管检查仍不能将未来合法退款释放错误判定为违规，实施.5时按原交接扩展，不删除历史保护样本。

## B-05.4 退款事实与A同步交接（2026-10-11）

V16/46表已执行，冻结版本全量追补与新版本原子Outbox、严格退款签名回执/Event.query/typed Trade.query、高水位与隔离已完成；同包实际A停启/乱序/新B进程及原链路回归见过程13.2。原支付Outbox字节与资金不动，退款成功/A同步分别保留；DEFERRED_B05义务未因资金DONE或A ACCEPTED伪称库存收尾完成。B-05.5仍须核验全额退款/不履约证明并原子释放，仅清原guard；原成团CONFIRMED/PENDING不得回退。异常未具合法资格保持隔离，不能编造CANCELLED_LATE_PAYMENT证明或核对声明。主B路线图仅同步推荐D18～D20块，A外部并行源文件不动。

## B-05.5 已接续的库存与运营边界（2026-10-11）

V18/48表，可信全额退款及原不履约证明下的唯一RELEASE、订单/仅本单guard/原义务原子收尾已实现；A离线及新B重放/恢复后同步实测通过，原成功支付和原事件字节不回退。六HTTP、本人退款摘要与运营退款/核对页面及持久查单/重试审计完成，详见B-05过程14.3和路线图23.13。

B04HandoffCommands只读审计现按完整退款根/成功事实/资格/释放证明绑定/唯一流水校验合法付费RELEASED，UNKNOWN释放仍违规；不是豁免全部已付款释放。新批次b055-20261011-handoff审计通过。原成团CONFIRMED/PENDING不可回退，缺可信资格/同步明确冲突者保留库存与隔离。取消后收款没有伪造资格生产，ALREADY_RELEASED严格历史核验分支的完整正向异常验收及其他全故障矩阵留.6。

## B-05.6已接续与B-06入口（2026-10-11）

本交接原D6工作/资金/库存约束已在B-05新联合总批b056-20261011-01支持范围验收：真实A无人付各一次原关闭释放、部分付原90收款全退及A停启/新B原证明重放、全付最后原事件竞争3CONFIRM/PENDING零退款。原B04三专项及证明感知只读审计均通过，旧UNKNOWN/HELD/guard/资金与原文不删除。精确原始证据/来源/包指纹见B-05过程15.2和tests/b05-joint-acceptance.json。

下一阶段入口[b05-b06-handoff.md](b05-b06-handoff.md)。取消后异常收款正向自动资格未开放，受控矛盾安全隔离已验，不能说ALREADY_RELEASED异常资金正向全链已通过；新渠道若关后可收款必须另设计。B-06部署/备份/生产或跨机故障尚未做，B05未提交或推送。
