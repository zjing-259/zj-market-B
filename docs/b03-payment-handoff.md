# B-03向B-04／B-05交接

更新：2026-10-09。对应唯一[B-03开发过程第18节](b03-development.md#18-b-036-联合故障验收与交接2026-10-09已完成)。本文是接续清单，A字段及消息规范以[A/B契约](../../group-buy-market/docs/ab-api-contract.md)为权威；不复制协议，不表示支付功能已经实现。

## 1. 已实现事实与标识

| 对象 | 当前权威事实 | 接续要求 |
| --- | --- | --- |
| 商城订单 | b_market_order.order_id就是A的outTradeNo；user/source/channel来自服务端确认，purchaseIntentId绑定原请求；confirmationId一次绑定 | 支付/退款必须关联原订单，不能把一次网络重试变成新购买；不接受浏览器提交可信userId或渠道作用域 |
| 冻结购买条件 | PurchaseConfirmation.conditions及商品快照；金额为精确两位小数/CNY，单SKU/数量1，原价－优惠＝实付；reserve_request和hash永久保持 | 支付金额取已受理冻结条件且与可信A成交结果一致，不重新采用当前商品价、浏览器价或试算缓存 |
| A占位证据 | ReservationEvidence含A orderId/teamId、recordVersion/teamVersion、成交条件、reservedAt/paymentDeadline/serverTime；有摘要和接收时刻 | 后续消费/查询仍验证所属、版本及原条件；同版本异事实/金额/身份/团队矛盾不能强行覆盖 |
| 库存 | b_inventory_reservation单订单唯一HELD；b_inventory_account维护available/reserved/sold；流水业务唯一键 | B-03只落地预留及未支付RELEASED；InventoryAccount.confirm规则存在，但CONFIRMED的业务持久提交入口尚未实现，不把领域方法当成成团履约已接通 |
| 购买守卫 | b_purchase_guard同用户同SKU限制一笔未结束购买，跨活动/团队互斥 | 已付待成团继续占守卫；完成成团库存确认，或失败全额退款且释放后才解除 |
| 关闭 | 严格未发为LOCAL_NEVER_DISPATCHED；可能已发为冻结closeId/reason/paymentDisposition/verifiedAt及hash，真实close后query确认 | 原关闭重试不能更新时间/换closeId/改正文；普通用户不决定资金状态。CLOSED、RELEASED、余额、流水、guard、任务同事务 |
| 任务与审计 | 一单一条b_trade_coordination，独立b_trade_attempt；lease/token/intent fencing，可能已发标记先提交；b_order_operation原键/原参/版本/原因/受理快照 | 网络与数据库事务分离；租约/令牌与业务状态在锁后取时校验。异常控制只能原任务；鉴权CHECK只读核验，失败停留，证据矛盾不可页面恢复 |

## 2. 支付开放前必须改变的安全边界

当前paymentExposure恒为NEVER_OPENED、paymentEnabled=false，没有渠道支付/退款表、资金回调或支付事实发布。可信PAID、payment/refund、COMPLETED等与当前范围矛盾的事实会进入核对并保留HELD；这是保护边界，B-04必须有计划地扩展。

创建任何渠道支付请求之前，先在本地事务持久支付意图、稳定支付业务键、冻结金额/期限以及“支付可能已开放”的事实并提交，之后才外调。外调超时也不得回到NEVER_OPENED。与取消使用同一订单/库存/任务并发边界，杜绝支付已在途但取消仍按未开放释放。

先停止新付款，再核验原渠道支付单。可信已付走支付确认及可靠事件；确定关单未付才允许凭服务端证据声明CLOSED_UNPAID；UNKNOWN继续持有库存和购买守卫。A CANCELLED不是渠道未收款证明，浏览器返回页、HTTP超时、一次NOT_FOUND均不能替代渠道事实。已有冻结NEVER_OPENED关闭请求不得在支付开放后原键改写；支付与关闭的互斥/迁移方案须在B-04设计确认。

## 3. 截止、成团和退款

- A的合法付款窗口为[reservedAt,paymentDeadline)，使用可信渠道paidAt；不能以通知到达时间判断是否在窗口内，不接受未来支付时间。B的a_deadline_due_ms只是调度提示，查询A的serverTime/权威期限后再处理，不凭页面倒计时释放。
- 窗口内已付但通知迟到，可靠发送原PAYMENT_SUCCEEDED并以queryEventResult及Trade.query确认A已接受；Broker ACK不是PAID_ACCEPTED。已付待成团继续HELD和同SKU守卫，A确认COMPLETED后才以独立幂等事务HELD→CONFIRMED、reserved减一/sold加一、唯一CONFIRM流水及守卫处理。
- A进入RECONCILING时，后台查询其冻结reconciliationId/rosterVersion/完整名单；未知资金/缺单/矛盾不提交伪完整核对。不将名单、他人订单或后台核对RPC透传商城。
- A失败且渠道确认全额退款成功后，才释放已付订单库存；退款请求、退款事实、库存释放各自幂等。迟到或重复TEAM_FAILED、退款回调/查询和REFUND_STATUS_CHANGED不能多退、多释放或复活。窗口外已收款形成独立退款义务，不冒充未支付关闭；A退款名单不能再为同单创建第二笔退款。

## 4. 待实施端口与可靠消息

| 能力 | 必须保留的语义 | 当前实现边界 |
| --- | --- | --- |
| 创建支付 | 稳定paymentId、原订单、冻结实付/CNY/权威截止、不可变请求；出站前持久开放标记 | 未实现，渠道和SDK未选择 |
| 查支付/关支付 | 原稳定键、可信PAID/CLOSED_UNPAID/UNKNOWN、金额/真实paidAt/验真证据 | 未实现；UNKNOWN不释放，不凭NOT_FOUND换键 |
| 验证支付通知 | 来源/验签/防重放、业务关联、金额/币种、事实去重；本地提交后确认回调 | 未实现；前端不能伪造成功 |
| 退款/查退款 | 原支付/全额金额、稳定refundId及请求摘要、可信最终状态，未知持久恢复 | 未实现；不能用B-03取消测试替代真实退款 |
| 交易Outbox/Inbox | 支付/退款本地事实与事件同事务；原eventId/正文重投，Broker成功与A处理成功分开；A结果/团队事件提交后确认消费 | 仅商品可靠同步已经实现，b_product_outbox和SyncResultReader限定商品，不能把交易正文塞入商品表或放宽商品结构校验 |

复用独立ContractCodec、现有签名/外部密钥、租约/持久隔离/原事件补查原则；新增支付/退款事件仓储与消费者按现有七模块放置。RPC保持新requestId/nonce，MQ业务重投保持原eventId和不可变正文；业务唯一键同时覆盖不同eventId的相同支付/退款。EVENT_PROCESSING_RESULT与TEAM_COMPLETED/RECONCILIATION_REQUIRED/FAILED按契约分别验证、持久去重和版本推进，结果不生成结果循环。

保留原全局锁序：用户→商品→guard→库存→订单→预留→协调任务；新增支付/退款/Inbox/Outbox锁位置须在B-04设计逐项确定，不能在任意旧入口倒序加锁。新表以V10及后续新迁移实施，先独立验收库再开发库/最小运行授权，绝不改写已执行V1～V9。所有渠道网络调用在本地事务外。

## 5. B-04开始时需逐个确认的方案

真实支付渠道/沙箱及SDK、支付方式/支付尝试模型、可信回调接入条件和密钥轮换、资金证据保存与脱敏策略、支付与原关闭请求互斥/迁移、资金任务与新增锁序，以及首版退款能力范围均未在本阶段默认选定。根据渠道能力比较后逐个交用户选择；不因为本阶段验收通过自动开放资金入口。

B-04新增验收必须覆盖：创建渠道单前后崩溃、支付响应丢失原键恢复、支付和取消并发、关单返回未知/已付、截止前付款通知迟到、窗口外收款退款、相同paymentId不同事件、重复/乱序结果、成团只确认一次库存，以及实际回调验真与权限。B-05补齐完整名单核对、缺单/资金未知保留、A失败全额退款后一次释放、多次重启和重复退款回调。真实渠道未接通的项目必须标为未验收，不能引用B-03的NEVER_OPENED测试作为资金最终性证据。

## 6. 当前运行及验收入口

普通商城使用scripts/start-market.ps1，B显式JDK21，终端/A仍Java8；数据库、RPC、MQ、JWT密钥均外部注入。数据库V9/21表运行DML，无DDL/Flyway/A/system/grant权限，普通启动不迁移。运营核对按既有原键控制接口，不提供SQL改成功/释放未知库存的交接命令。

统一验收docs/tests/run-b03-acceptance.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <新唯一批次>。真实A、真实B MySQL与受控远程故障端口、真实Edge页面分别记录证据；最终批次b036-final-20261009-scoped已通过（43项JUnit及全套联合故障/真实A停启/B进程恢复/页面），报告target/b03-acceptance/b036-final-20261009-scoped/report.json；指纹和局限以唯一B-03过程第18节为准。B-03本轮不修改A源码、日常A库或清除未知历史库存，不提交/推送未经用户要求的内容。

## 本次任务复杂度

交接文档复杂度中等，依赖已确认D1～D33与真实代码/契约；B-03.6联合验收复杂度高，按组合竞争→同批指纹与证据→真实A/B重启与回归→守恒→资金接续→安全清理六步收口。未来支付属于更高风险的新阶段，先确认方案及不变条件，再设计表与事务并接渠道，不在本文提前实现。
