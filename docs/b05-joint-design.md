> 当前状态（2026-10-11）：B-05.6联合故障验收与B-06交接已完成支持范围内验收。最终同包106项JUnit/前端构建、新SQL及跨JVM/浏览器、真实A无人/部分付款停机退款释放/全付款最后事件成团竞争、逐单资金库存及A名额只读核验、原三专项/交接审计/普通启动均通过。推荐D26～D28已写双路线图，证据及边界见[b05-development.md第15.2节](b05-development.md)、[B-06交接](b05-b06-handoff.md)与[持久验收摘要](tests/b05-joint-acceptance.json)。取消后异常收款正向自动资格未开放，隔离验收通过；此限制不宣称全自动闭环。b-05/53ad32d，全部成果未提交/合并/推送，B-06未开展。下文旧阶段状态保留历史时点。

> 当前状态（2026-10-11）：B-05.5库存收尾及运营页面已完成本阶段验收。双B库V18/runtime48表精确DML；最终同包106项JUnit、SQL05及跨JVM、实际B HTTP浏览器04、真实A live02停机退款/释放/新B重放/恢复后同步、原关单/结算/履约回归、只读交接审计及普通启动均通过。推荐D21～D25已写双路线图，详情见[b05-development.md第14.3节](b05-development.md)。最终只读归档target/refund/b055-20261011-delivery-03/report.json；.6完整联合故障矩阵未开展。b-05/53ad32d，全部阶段改动未提交/合并/推送。下文带日期的旧状态保留历史时点。

> 当前状态（2026-10-11）：B-05.4可信退款事实与A同步已实现并通过同包业务验收；b-05/53ad32d，阶段变更未提交/合并/推送。双B库V16/runtime46表精确DML；103项JUnit、SQL03/跨JVM、实际A live-02停启/签名MQ/严格查询/新B进程、关单/结算/履约回归及普通启动通过。推荐D18～D20已保存双路线图；最终归档见target/refund/b054-20261011-delivery-02/report.json，过程见[b05-development.md第13.2节](b05-development.md)。付费HELD/guard保留；库存释放/HTTP/页面归.5、完整联合矩阵归.6。A外部并行改动保持，实际验收A包及契约不变。下列旧状态保留历史时点。

> 当前状态（2026-10-11）：B-05.3独立模拟退款已完成并验收通过；b-05/53ad32d，全部阶段变更未提交/合并/推送。双B库V15、runtime46表精确DML；99项JUnit、同包SQL/跨JVM、真实A完整核对资格及自有A停止后独立退款、关单/结算/履约回归和普通包默认启动通过。新增推荐D15～D17已保存双路线图。最终报告target/refund/b053-20261011-delivery-02/report.json；详见[B-05过程12.2](b05-development.md)。退款MQ/库存释放/运营及页面归.4/.5，.4～.6未开展；下列旧状态保留历史时点。

> 当前状态（2026-10-11）：B-05.2到期完整核对已完成并验收通过；工作树D:/Java/zj-market-b-05，分支b-05/53ad32d，改动未提交/合并/推送。双B库V14、41表精确DML；87项JUnit、最终同包真实A成团竞争/部分付款丢响应跨JVM恢复、SQL及关单/结算/履约回归通过。最终报告target/reconciliation/b052-20261011-delivery-03/report.json；详见[B-05过程11.4](b05-development.md)。退款义务已持久化，资金仍NONE、付费HELD保留；退款执行归.3，.3～.6未开展。下列暂停及旧阶段记录保留历史时点，以本条和11.4为当前状态。

> 当前状态（2026-10-11）：用户明确要求暂停B-05.2，等待用户明天说“恢复工作”后继续。.2尚未完成，不自动推进.3。代码和双库V14/41表保留，87项JUnit及最终SQL批次07、真实A部分付款批次live-02已通过；成团竞争批次completed-01由用户暂停中断，尚无通过结论，受影响专项回归及最终文档收口待做。工作树D:/Java/zj-market-b-05、分支b-05/53ad32d；未提交/合并/推送。完整恢复清单见[B-05过程11.3](b05-development.md)。

# B-05.1 核对与退款联合设计

2026-10-10设计归档时点：设计完成，尚未编码执行器或执行迁移；当前实施状态见顶部及下表。实施工作树D:/Java/zj-market-b-05，b-05/53ad32d。用户授权新增选择按推荐决定并记录路线图；B05-D1～D3及B04-D1～D7保持。选择总表见[路线图23.2](development-roadmap.md)，过程/验证见[B-05第10节](b05-development.md)。术语见[业务语言](../CONTEXT.md)。

## 1. 事实来源、范围与差距

先读docs持久化入口、[B04→B05交接](b04-b05-handoff.md)、B05.0新批次证据，再核对当前源码与[A契约8.3/8.4](../../group-buy-market/docs/ab-api-contract.md)。A契约SHA256为83b02a7ebf5e80b5ef4d1b03936e6b1ca33eed32f6d9c68b451e855c6192d7dd；A V2TeamEngine.complete/outsideWindow、V2EventEngine退款处理与契约一致，不改A。

基线已有V13/35表、独立支付、原资金与支付Outbox、冻结未付关闭、可信成团CONFIRM/PENDING。DEFERRED_B05只是持久承担。B05.0的77测试和真实A成功链路属于基线历史证据，不算本设计退款验收。

| 当前代码约束 | 必须改造的阶段/模块 |
| --- | --- |
| PaymentClosingRepository及FulfillmentRepository用review_required总开关；RECONCILING与证据冲突混合 | .2引入有归属的临时阻断；只给核对协调器窄权限继续查单/未付关闭；.5成团恢复不误清冲突 |
| SettlementRepository保存第一份work原字节，合并reasons；A拒绝会建义务 | .2关联后续Inbox原文；义务与退款执行资格分开；A拒绝本身不能直接触发退款 |
| V11 Outbox CHECK仅PAYMENT_SUCCEEDED/version1；payment_id NOT NULL、uk_trade_fact三列唯一 | .4增量扩展类型/绑定/版本；支付约束保持；所有按payment查Outbox的代码按类型筛选并稳定锁序 |
| TradeMessageReader忽略非支付结果；RocketMqSettlementTransport发布/查询硬编码支付；无核对端口 | .2新增TeamService核对适配端口；.4严格退款结果分支、原Event.query及Trade.query补偿；不放宽商品reader |
| V9 CLOSED仅两种未付basis；V7 ledger以order/kind唯一 | .5增加FULL_REFUND_CONFIRMED及退款收尾证据，保留唯一RELEASE；不复用未付证明、不回滚sold |

首版仅全额、后台退款；不增加买家主动退团/部分退款/真实第三方资金/逆向履约/发货。已CONFIRMED或PENDING与失败退款矛盾立即隔离。

## 2. 对象、标识与不变量（D4、D5）

- reconciliationTaskId是B内部任务ID；A的(source,channel,teamId,reconciliationId,rosterVersion)唯一识别一份冻结名单。成员键为(taskId,outTradeNo)，max100，完整精确集合，不因后来取消删成员。缺本地成员也持久保存，不给member.local_order_id强制FK。
- completionId独立服务端生成，不复用refundId；一份核对任务最多一份冻结提交。checkedAt、按outTradeNo排序的完整results、源/渠道及原请求业务字节/hash同事务冻结；每次重试仅更新RPC鉴权nonce/签名，业务字段不变。
- refundId稳定绑定一个orderId/paymentId/原成功渠道流水；UNIQUE(orderId)、UNIQUE(paymentId)，全额等于原冻结成功金额，CNY、十进制定点金额，不接收客户端金额。原支付成功及paidAt永久保留。
- refundAttemptId是内部执行键，UNIQUE(refundId,attemptNo)。明确FAILED才创建下一尝试；UNKNOWN/超时/丢响应使用原attemptId/refundId及原请求查询或幂等重发。最多一个未决尝试，成功后禁止新尝试。
- work REFUND_OBLIGATION仍以paymentId:orderId唯一。多原因只合并责任；b_trade_evidence_link关联每份Inbox/原work证据，保留原文SHA与规范事实SHA的区别。不能把第一份work证据当作全部原因。
- 原渠道payment根上串行验证成功金额与累计成功退款；每个payment最多一个refund根，全额成功累计等于原收款，失败/未知不增加已退款额。相同ID异请求隔离，不以新ID规避冲突。

## 3. 完整核对流程及稳定提交（D5、D6、D11）

1. 可信TEAM_RECONCILIATION_REQUIRED/TEAM_FAILED持久Inbox、游标、旧work后接管；扫描DEFERRED_B05不能误扫成团已完成工作。先事务外TeamService.query确认当前终局；COMPLETED转原成团路径，不能要求它必须已有核对名单。仍RECONCILING再用TeamService.queryReconciliation获取完整名单/版本，保存查询来源、响应业务字节/hash、观测DB时间。单订单Trade.query仅是成员证据。
queryReconciliation返回RECONCILIATION_NOT_STARTED时再查Team.query；FORMING按A期限继续等待，不把NOT_STARTED当空名单或FAILED。
2. 每成员单独短事务：核对归属与冻结A订单/user/team/金额/窗口，创建RECONCILIATION临时阻断，停止新支付及失效旧支付任务intent/token；未开放原请求永远保留NEVER_OPENED，可能开放则走原根queryClose/closeRoot，不能凭一次attempt失败判未付。核对协调器允许越过自己拥有的临时阻断继续收集证据，不能越过真正冲突。
3. 渠道PAID：通过原M2核验原paidAt/金额/所有绑定。窗口内且A仍可接收，用原PAYMENT_SUCCEEDED Outbox/Trade.query确认A已PAID且paymentId相同，再形成PAID_ACCEPTED。窗口外收款先持久refundId和义务，形成PAID_OUTSIDE_WINDOW；不等待退款完成，不伪造普通支付Outbox。A取消后窗口内迟到收款独立退款义务，不能谎称超窗；冻结名单内按其真实A CANCELLED/closeId及完整渠道事实判断能否提供合法成员声明，冲突不能用CLOSED_UNPAID掩盖收款。
4. 渠道完整CLOSED_UNPAID：验证根关闭证明覆盖全部尝试并禁止再付；以原closeId请求A关闭，Trade.query确认CANCELLED并保留原closeId请求，才准备CLOSED_UNPAID声明；A最终核对提交校验closeId是否匹配。未付可沿原关闭原子释放，不等其他成员退款。
5. UNKNOWN、缺本地成员、归属/金额/版本冲突不可提交。名单空集合只有A权威冻结名单确实为空才合法；不可用局部空查询代替。所有成员证据有来源、原请求/响应hash、proofVersion、观察时间及相关intent；等待任务始终可见。
6. 仅三个合法disposition齐备且集合精确相等，重新查A当前团队/核对身份并复核本地游标和成员证据版本后冻结唯一提交；锁释放后调用completeReconciliation。A内部对完整名单原子校验/裁决，B不持全团队订单锁或假装跨A/B事务。
7. 丢响应/暂不可用：SUBMIT_UNKNOWN，原completionId原业务请求重发并queryReconciliation/Team.query确认终局。A返回INCOMPLETE先重查原依赖，原声明不变可重试；身份/名单/异事实冲突转REVIEW_REQUIRED。已冻结请求不自动另造completionId；未冻结草稿可重建。牺牲自动改写错误声明的便利，保留审计和人工诊断，不用换ID绕过A冲突。
8. 核对期间最后付款可能使A COMPLETED；以当前可信COMPLETED及逐单资金证据回到原成团履约路径，仅解除本任务拥有的临时阻断。不得因旧FAILED/reconciliation工作退款或释放。可信FAILED才为其已接受支付建立执行资格；超窗责任单独保留，不依赖refundRequiredOutTradeNoList含它。

接口限制：A Reservation和CloseResponse均不返回closeId，close重放遇到已CANCELLED甚至可能沿用另一关闭记录。因此query CANCELLED不能证明closeId匹配；B只提交本单已冻结的原closeId，正常单写者关闭链路恢复，最终由A complete原子验证。INCOMPLETE不得换closeId或造未付证明；不确定其他关闭来源时隔离并诊断。此限制不要求修改A。

状态：核对task DISCOVERED→COLLECTING→READY→SUBMITTING→SUBMIT_UNKNOWN/RESOLVED；任何非终态可WAITING_DEPENDENCY，证据矛盾→REVIEW_REQUIRED。成员 WAITING→PAID_ACCEPTED/CLOSED_UNPAID/PAID_OUTSIDE_WINDOW；缺失MISSING_LOCAL、未知UNKNOWN或冲突REVIEW_REQUIRED均非可提交结果。冻结提交状态FROZEN/SENDING/UNKNOWN/ACKNOWLEDGED/REVIEW_REQUIRED，RESOLVED必须有可信A终局；Broker ACK不是终局。

## 4. 临时阻断及退款资格（D6、D11）

b_order_block区分RECONCILIATION与EVIDENCE_CONFLICT，记录ownerTeamId（实际ownerId=teamId）、ownerVersion、reason、ACTIVE/CLEARED、证据链接。旧review_required作为兼容投影，不能全局UPDATE false；新增路径在同一订单事务重算。迁移时无法可靠归因的旧true记LEGACY_REVIEW并保守保留，只有原文/游标及其他原因可证明单纯正常核对时才分类为临时阻断。TEAM_COMPLETED不会清除SIGNATURE/FACT/LEGACY冲突。

义务状态不等于可执行。eligibility三种：TEAM_FAILED_ACCEPTED（完整可信FAILED和本单A PAID/payment绑定）；OUTSIDE_WINDOW_RESOLVED（原completionId成功提交/重放返回FAILED，可结合冻结完整请求证明A已登记本单异常payment/refund，且团队终局不履约）；CANCELLED_LATE_PAYMENT（A本单权威CANCELLED、本地原关闭依据及原渠道收款，符合契约8.4异常退款条件）。A_REJECTED/超时/缺订单/签名错误仅线索，暂不具资格；A FORMING/COMPLETED下普通已付不得盲退。既有CONFIRM/PENDING或互相矛盾终局一律隔离。

A的核对快照不直接返回异常收款登记，单查FAILED不证明自己的超窗声明已应用；丢提交响应后须原completionId原请求重放成功，不能编造查询中不存在的exception/refund关联。complete返回COMPLETED会跳过异常成员处理，不能作为OUTSIDE_WINDOW_RESOLVED依据；若本单另有可信CANCELLED证明可走契约允许的迟到收款退款，否则保持可见隔离，不退款普通已接受成团付款。

查到资格后冻结完整eligibilityProof/hash/source/teamVersion/ArecordVersion/本地intent；退款调用前订单锁内再校验原证据版本和无履约事实。不因A退款ACK缺失阻止执行；没有有效资格则保留WAITING_ELIGIBILITY而非编造A终局。

## 5. 独立退款、可信事实及恢复（D4、D8、D10）

商城退款单分开显示：fundsStatus NONE/PENDING/UNKNOWN/FAILED/SUCCEEDED；syncStatus NOT_CREATED/PENDING/ACCEPTED/WAITING_DEPENDENCY/REVIEW_REQUIRED；releaseStatus HELD/READY/RELEASED/ALREADY_RELEASED/REVIEW_REQUIRED。资格/隔离单独字段，不把A回执当资金成功。

M1：订单完整锁前缀内建立/领取refund执行意图，验证资格与全额绑定；持久attemptId、不可变渠道请求/hash、可能已发送标记、intentVersion、token/lease，提交后调用IRefundChannel.execute/query。提交前崩溃无调用；提交后崩溃由原键查询/幂等重发恢复。

C1独立渠道事务：先锁原b_sim_payment成功根，再refund根/attempt；核对原支付成功ID/金额、币种/订单，成功退款总额上限及原请求。正常路径自动SUCCEEDED，渠道DB时间refundedAt+原退款事实hash与持久通知同事务；UNKNOWN/FAILED/丢通知仅verification工具制造。渠道UNKNOWN无法推定FAILED，退款UNKNOWN不阻塞其他订单扫描。

M2：通知仅唤醒；事务外查原渠道记录，严格核对完整绑定/金额/状态/渠道时间，不接受浏览器或任意内部消息自报成功。资金事实及对应退款版本事实在同一商城事务提交（D15：.3冻结版本字节/hash，.4增量扩展Outbox后原子幂等补建），再经原渠道查询与已持久事实核对ACK通知。失败/UNKNOWN不改原支付成功；退款SUCCEEDED不可退回，重复比较同一事实，不只比较通知ID。通知ACK/retry先锁行再取DB时间校验state/token/lease；旧令牌拒绝。

明确FAILED自动新attempt、原refundId；下一尝试建立时产生新PENDING版本。UNKNOWN仅查原尝试，不新建attempt。异常来源不可信/同版本异事实/超额或已履约→隔离，不自动退款重试。

任务扫描2秒；单次外部调用超时10秒、RPC retries=0；商城/渠道通知租约30秒，20秒前续租须锁后时间校验，续租失败停止本地写回。重试2/4/8/16/30秒封顶+jitter0～250ms；连续5次失败告警，保留自动恢复不熔断丢单；成功后重置连续技术失败计数但保留历史。A Outbox沿原1/2/4/8分钟退避。参数可配置且启动验证正值、timeout<lease、续租间隔<lease；改变参数需记录，不改变幂等规则。

## 6. 退款版本、Outbox与A结果（D7）

refundVersion为每个refund严格递增正BIGINT，序列化十进制字符串，不按时间生成；新增可对外事实PENDING/FAILED/SUCCEEDED才加1。内部UNKNOWN仍投影原PENDING，不另发UNKNOWN。先持久资格才开始PENDING版本；多个内部查询不生新版本；FAILED→新尝试PENDING→SUCCEEDED允许，SUCCEEDED终结。

V16保留uk_trade_fact(payment_id,event_type,fact_version)，增加nullable refund_id和复合FK(refund_id,payment_id,order_id)绑定b_refund唯一父键。支付CHECK为type=PAYMENT_SUCCEEDED、version=1、refund_id NULL；退款CHECK为type=REFUND_STATUS_CHANGED、version>=1、refund_id非NULL。原V11未命名CHECK须通过information_schema按原表达式精确定位/断言后替换，不能假设MySQL自动生成名。一个payment首版唯一refund，三列键支持多版本且保住支付唯一；旧Outbox正文/hash/eventId原字节不改。

每版本冻结独立eventId/occurredAt/payload/业务字节/hash；网络鉴权签名按既有机制。payload遵契约：userId/outTradeNo/paymentId/refundId/refundAmount/CNY/refundStatus/refundVersion/occurredAt；取消后异常收款额外原paidAt/paidAmount。原paidAt不以退款时间代替。不要求不存在的支付Outbox才能发送异常退款。

独立交易consumer原组复用，TradeMessageReader对REFUND_STATUS_CHANGED结果增加严格分支：producer/签名/消息元数据/原eventId/源渠道/业务关联、unknown字段/重复键/尾随字节/大小和精确结果字段校验。商品SyncResultReader不改。查询补偿用原IntegrationService.queryEventResult及完整TradeService.query的typed退款视图，记录RPC来源，不生成虚假A消息。新增IReconciliationPort隔离A DTO，IRefundChannel隔离渠道事实，IRefundTransport隔离发送/查询；七模块依赖方向不变。

A旧退款版本处理可能返回已存在更高refundVersion：同版本必须与本地对应不可变状态一致；高版本只有本地已持久同refund的相应版本/状态且权威完整查询绑定一致才可认可；未知更高版本/相同版本异事实隔离。低回执不降低本地当前版本或ACCEPTED高水位。严格核对outTradeNo/refundId/status/version/recordVersion，不错误要求所有旧事件回执必须等于旧version。WAITING_DEPENDENCY保留原事件重试；Broker ACK不变ACCEPTED。A拒绝绝不回滚已发生的退款。

## 7. 库存与guard原子收尾（D8）

释放前须：原渠道收款SUCCEEDED、匹配全额退款SUCCEEDED可信原事实；原订单/支付/退款绑定；可信不履约终局/取消证明有效且无冲突；无CONFIRMED/PENDING；本地版本/租约仍有效。A退款ACK不是前置，A离线已有有效终局证明仍能收尾；缺终局证据继续等待。新的更高矛盾游标使旧proof失效并隔离。

HELD路径同事务：reserved→available（sold不变）、reservation RELEASED、唯一ledger(orderId,RELEASE)、b_refund_release证据、订单CLOSED/closedAt/basis FULL_REFUND_CONFIRMED、仅DELETE guard WHERE order_id=本单、收尾work DONE。每步故障全回滚；重复验证原release后幂等返回，不清后来订单guard。退款消息同步work仍独立，不因释放DONE遗失A同步。

已由可信未付关闭RELEASED后收到异常收款：核对原RELEASE流水及关闭证明，退款成功仅插b_refund_release outcome=ALREADY_RELEASED关联原ledger，不再增加available或新RELEASE、不改原close_basis/closeId/关闭时间、不删后来guard。缺原释放证据或CONFIRMED矛盾隔离。支付SUCCEEDED事实永久保留，订单查询显示资金已退而非从未支付。

## 8. 事务边界、锁序与fencing

既有相对顺序保持，统一完整序为：user→product→guard→inventory account→order→reservation→trade coordination→payment→payment attempts→payment operations/order operations（各按稳定ID）→payment task→order block→refund→refund attempts→refund task→Outbox（eventId升序）→team cursor→reconciliation task→members（outTradeNo升序）→submission→trade work→fulfillment→refund release→refund operation。多行同类按主键，缺guard也按已有用户/商品前缀串行。claim和complete共用helper，不能先锁work再反锁订单。

团队聚合事务只锁team cursor/reconciliation task/members/submission，不再回锁订单；逐成员事务按上述前缀，不持一单锁遍历其他单。冻结的是已确定不可变支付/关闭事实和成员proofVersion；准备冻结前事务外再查A，A提交原子校验并发变化，B收到响应后再次校验游标/任务版本。不同团队可并行。Fulfillment.complete目前按payment锁全部Outbox，改为明确类型并排序，所有旧B04收款/关单/履约代码亦须检查新阻断和退款边界。

渠道全局序独立：sim payment root→sim refund root→refund attempt→refund notification；通知领取/ACK不回锁渠道根。商城事务内不调用渠道/A/MQ；渠道事务不回调商城。每次认领/续租/写回先锁相关行，再另取数据库当前时间，必须state、token、lease_until>now、intentVersion和proofVersion匹配；锁等待跨租约、旧token被替换均拒绝提交。外部已发生动作不能撤回，过期响应只唤醒新处理者按原键查询，不擅自覆盖新事实。

## 9. V14起迁移及权限计划（V14/V15已落地，V16起待实现）

| 迁移/阶段 | 新表与关键约束/索引 | 累计runtime表 |
| --- | --- | --- |
| V14/.2 | b_reconciliation_task：PK taskId，UNIQUE(scope/team/reconciliation/roster)，state/nextAttempt/lease索引；b_reconciliation_member：PK(taskId,outTradeNo)，A冻结成员原文/proof/hash/状态，localOrder可空；b_reconciliation_submission：PK completionId、UNIQUE taskId，原请求/hash不可变；b_refund：PK refundId、UNIQUE orderId/paymentId、复合唯一(refundId,paymentId,orderId)，FK order/payment，原收款快照/资格/义务证据；b_trade_evidence_link：PK(workId,inboxId)，保留原文引用/hash，不抛弃缺本地work；b_order_block：PK(orderId,kind,ownerId)，ACTIVE索引和原因归属 | 41 |
| V15/.3 | b_refund_attempt：PK attemptId、UNIQUE(refundId,attemptNo)、一个活动尝试由refund.currentAttemptId锁内约束；b_refund_task：PK refundId，due索引/token/lease/intent；b_sim_refund：PK refundId、UNIQUE paymentId、原请求/累计成功金额；b_sim_refund_attempt：PK attemptId、UNIQUE(refundId,attemptNo)、原请求/hash/渠道事实；b_sim_refund_notification：PK noticeId、UNIQUE(attemptId,factVersion)、due索引及锁后ACK；扩展b_refund执行与事实字段 | 46 |
| V16/.4 | 无新表；扩展b_trade_outbox类型/版本/退款复合绑定和b_refund同步高水位/退款事实版本，reader/transport随迁移就绪后开启 | 46 |
| V17/.5 | b_refund_release：PK orderId、UNIQUE refundId、FK原RELEASE ledger及订单/退款，proof/hash/outcome；b_refund_operation：PK(actorId,operationId)、绑定refundId/action/expectedVersion/原请求hash/审计结果；替换ck_closed_basis包含FULL_REFUND_CONFIRMED，扩展查询投影 | 48 |

V14六表已按实际DDL在双B库执行，runtime41表DML已验证；V15五表亦已在双库执行，runtime46表DML已验证；V16～V17仍为计划，不拿计划声称已迁移。ID ascii_bin VARCHAR64，hash CHAR64，原文LONGBLOB，金额DECIMAL与现有一致，时间BIGINT DB毫秒、版本BIGINT正值，CHECK枚举/非负/lease成对/事实字段成组，所有FK/索引命名明确。新表中b_trade_evidence_link只关联存在的work/Inbox，不要求order存在；missing member不猜FK。退款根总计上限需原支付根锁+CHECK并用真实并发验收，不能靠普通跨表CHECK假装实现。

运行账号精确授权已有表和本步新增DML，无DDL/history/A/system/grant；verification迁移账号显式执行校验，普通包无Flyway。旧V1～V13含10.1、历史原文/资金/HELD/guard不修改或清除。新开关b.reconciliation.enabled、b.refund.enabled默认false；原trade.events开关只控制消费，恢复开关独立；关闭新写不应终止已承担资金的查单/通知/Outbox/收尾恢复，恢复开关默认开启但只处理已有意图。启动迁移能力检查避免旧schema提前执行。具体配置归.2/.3实现，普通支付不自动开启。

## 10. HTTP与页面（D9）

独立增量契约[b05-http-api.json](b05-http-api.json)，标记design-only，6操作：本人订单退款摘要；运营退款异常分页、退款详情、退款CHECK/RETRY；运营核对分页及详情。总前缀/api/v1，ApiResponse保持code/message/data/requestId，X-Request-Id、Cache-Control:no-store。security BearerAuth；运营后端角色OPERATOR，买家只看本人、异主404，未建退款本人200 refund=null。

CHECK只唤醒原渠道/A查询，不新attempt、不改变资金；RETRY仅可信资格且明确FAILED、无活动UNKNOWN/成功/隔离时安排自动同边界的新attempt。稳定operationId由客户端提供，(actorId,operationId)跨退款/动作全局唯一，同键异请求409；expectedVersion乐观冲突409，reason必填。新受理202/同键原结果200；操作审计与工作唤醒同事务。身份鉴权先于返回幂等快照；读接口不得触发业务写或查单。

普通订单结果页扩展可选refundSummary/reconciliationSummary，分别显示退款资金、A同步、库存收尾；技术token/hash/内部凭据不给买家。运营详情关联原工作/版本/失败码/告警/退避和完整名单缺项，敏感原报文只受控运维取证，不直接HTTP泄漏。桌面/窄屏恢复状态一致；不提供强制成功、手工释放、改金额/paidAt/名单或故障按钮。页面.5实现，.1没有路由已上线的声明。

## 11. 联合故障矩阵与验收责任

| 场景 | 持久承担与期望 | 实施验收 |
| --- | --- | --- |
| 全付/部分/无人付到期；最后付款成团 | 全名单精确结果；COMPLETED走原CONFIRM/PENDING，FAILED已付退款/未付关闭 | .2/.6真实A新B完整团队 |
| 截止前成功通知迟到；根关闭竞争；冻结旧NEVER_OPENED | 原paidAt、原键及根唯一裁决；UNKNOWN不提交/释放，旧声明不改 | .2真实MySQL+渠道+新JVM |
| 缺成员/缺本地/归属冲突/名单版本缺口 | WAITING_DEPENDENCY或REVIEW，禁止局部提交与猜user | .2/.6真实A及隔离注入分别记录 |
| complete已提交丢响应/提交前后崩溃 | 唯一completionId原字节恢复，A终局可信查询；冲突不换键 | .2新进程/实际RPC |
| 超窗收款无支付Outbox、取消后迟到收款 | 稳定义务/refundId，合法A异常依据，不伪造超窗或未付事实 | .2/.4/.6 verification事实+实际A |
| 同payment多个原因/重复不同eventId | 单一refund，多原始证据均可追溯；同eventId异文隔离 | .2/.3真实SQL |
| refund调用前/后崩溃、响应/通知/ACK丢失 | M1/C1/M2原键恢复，独立通知持久；≤1全额成功 | .3/.4独立渠道新JVM |
| 明确FAILED/UNKNOWN/连续失败 | FAILED退避新尝试、业务键不变；UNKNOWN原尝试，5次告警后继续 | .3时间可控注入+实际SQL |
| 退款版本重复/乱序/同版本异事实/旧结果返回新版本 | 单调资金/高水位，严验本地已知新事实，不降级/不伪造ACK | .4实际MQ/RPC及签名负例 |
| A离线/WAITING_DEPENDENCY | 有资格仍退款，Outbox持久；缺终局不能释放；恢复后原事件同步 | .4/.6实际A停启 |
| 锁等待跨租约、token替换、intent旧版本 | ACK/retry/收尾写回全部锁后时间fencing，旧处理者拒绝 | .2～.5真实MySQL行锁等待，不能只mock时间 |
| RELEASE流水后失败/并发重放/后来guard | 全事务回滚；唯一RELEASE；只清本单；ALREADY_RELEASED不再加库存 | .5真实MySQL/新JVM |
| 成团与旧失败/退款矛盾 | 不动CONFIRMED/sold/PENDING，隔离而非倒退履约 | .2/.5/.6原成功链路回归 |
| 买家越权/非运营/重复控制/关开关 | 404/403/409与审计；CHECK/RETRY不绕过资格，已有恢复持续 | .5真实HTTP/浏览器 |

.6必须实际A/MySQL/MQ新批次、完整B订单集合及A/B新进程、渠道/HTTP/浏览器分开标证；逐单收退款守恒、库存available+reserved+sold、团队名额及唯一流水守恒。旧protected记录缺失/改变0；不删除UNKNOWN/HELD/guard/失败批次。B04只读审计扩展合法退款RELEASED证明，而非取消UNKNOWN安全检查。

## 12. 本次设计验证与接续

运行docs/tests/validate-b05-design.py验证：OpenAPI引用/鉴权/字段/操作一致、精确名单与窗口及版本场景、退款原键/全额/释放守卫约束、迁移阶段表数、决策双文档同步、旧Java/SQL/接口及A契约指纹未改、Git差异空白。报告target/b05-design/b051-20261010-03/report.json；静态模型检查不是数据库/退款业务运行测试。

.1交付设计、增量HTTP规范和静态检查，不启服务、不运行迁移、不声称资金闭环已验。下一阶段.2实现V14最小义务/名单/冻结提交与阻断兼容；.3～.5依次落地。没有未答方案；遇到A真实能力差异、不可安全归因旧数据或逆向履约需求须保留证据再记录调整，不擅改现有边界。


## 13. B-05.2 实施对照（2026-10-11）

完整名单/成员进度、唯一冻结核对提交、原支付与未付关闭复用、稳定退款义务/资格、证据关联及teamId自有阻断已落地。V14六表、双库runtime41，87项JUnit及同包真实A/SQL/专项回归通过，批次与范围见过程11.4及路线图23.10。名单收集按D12单成员租约，终局逐成员独立事务fencing；原未知提交即使A已FAILED仍先重放原请求，不换completionId。COMPLETED可无核对名单，清自有阻断后由原成团工作确认库存。

.2只生成funds NONE义务/ELIGIBLE，不执行退款或释放付费HELD。V14的NONE约束须在.3用新增迁移扩展。第5节D10配置/续租中，核对扫描/超时/租约/退避已用固定默认值实现；退款参数配置及续租待.3。V15起、退款尝试/通知、版本Outbox、退款成功释放、六项HTTP/运营页面仍待.3～.5，联合全矩阵待.6。旧章节中的“未实现/尚未迁移”按.1设计归档时点理解，不能覆盖本节实施状态。


## 14. B-05.3 实施对照与B-05.4接续（2026-10-11）

独立全额退款渠道、商城M1/C1/M2、稳定refundId/多attempt、未知原键、明确失败新尝试、配置/续租/锁后时间、自动有界退避及告警、持久通知/可信查单后ACK已实现。当前复用.2产出的两类可信资格，调用前再次订单完整锁前缀验证；调用后出现矛盾则保存实际已退款事实并隔离。资金成功不释放HELD或guard。V15已执行，46表精确DML，99项JUnit及同最终包真实SQL/两JVM、真实A自然到期核对资格后自有A停止的独立退款/原专项回归通过，证据见过程12.2。

D15细化第5/6节阶段分工：.3用b_refund.fact_version单调生成对外PENDING/FAILED/SUCCEEDED版本，与行version分离；b_refund_attempt的pending/result版本、业务事实字节/hash及时间不可变，UNKNOWN保持原PENDING版本。.4新增Outbox时必须追补所有已冻结版本，包括资金任务DONE及已退款后隔离者；资金事实不可因缺A ACK或MQ不可用回退。按稳定版本唯一性原子补建事件，保留原支付Outbox字节和唯一键。本阶段没有退款MQ、严格退款回执、库存释放或六项HTTP/页面。CANCELLED_LATE_PAYMENT资格生产及证明适配未在.3伪造，留待后续明确路径；现有A_REJECTED线索不会直接执行退款。

D16退款时序已配置并启动校验timeout<lease、renew<lease；续租失败拒绝本地写回，原键外部事实由后继领取者查询恢复。D17仅扩展verification自有端口参数，默认50051/18091保持，本次显式50052/18092并贯穿环境基线；外部A进程/配置不动。V16退款Outbox及结果、V17收尾/审计、.6完整联合矩阵仍待实施。

## 15. B-05.4实施对照（2026-10-11，已完成）

V16、资金版本同事务Outbox、全部缺失冻结版本追补、严格退款签名结果/原Event.query/typed Trade.query、单调接受高水位及独立同步隔离已实现。D18～D20细化第5/6节，详细锁序/退避/故障历史与最终证据见过程13。原支付资金/Outbox、已退款资金不回退，付费HELD/guard保留至.5。CANCELLED_LATE_PAYMENT资格生产仍未伪造：当前渠道根关闭后禁止再收款；对不具合法核对声明的窗口内取消后收款继续隔离，不能冒充PAID_OUTSIDE_WINDOW或CLOSED_UNPAID。当前两类已实现资格均复制原支付异常字段同步；实际异常资金完整联合矩阵归.6验收。

15节收口：最终同包SQL03/实际A live02/原专项/普通启动全部通过，103项JUnit，最终归档delivery02见过程13.2。V16已应用；.5/.6未开始，未提交或推送。

## 16. B-05.5实施对照（2026-10-11，已完成）

原设计六操作已实现并完成真实HTTP/浏览器验收，最新接口状态见b05-http-api.json。V17增量新增b_refund_release/b_refund_operation，扩展独立release_status及CHECK标记；V18新增check_previous_due_ms，避免查单改变原退款执行计划。D21～D25在路线图，完整锁序/证明/幂等/权限和同包证据见过程14.3～14.4。A确认、渠道资金、库存收尾仍独立；明确同步矛盾保守阻断新释放。未取得的核对标识/版本nullable，列表0起始分页，与旧订单接口分开。

CHECK不创建退款尝试且恢复原任务状态/到期时间；隔离后仍能查原键但不解除隔离/不执行资金。RETRY需明确失败/有效资格/无活动租约，持久唤醒后由恢复器执行。原actor+operationId审计冻结请求及结果，授权先于重放。原已释放分支保守验证原未付关闭，不伪造取消后收款的资格或正向测试；完整异常矩阵归.6。

## 17. B-05.6联合验收对照（2026-10-11）

当前支持模拟渠道的联合矩阵同新最终包通过，实际A无人/部分/全付最后事件竞争、逐单资金库存与A名额、独立渠道故障/锁/跨JVM、六HTTP及浏览器和原链路回归见过程15.2、持久摘要tests/b05-joint-acceptance.json。D26～D28明确实际与受控来源；本阶段未改普通业务规则或V18。第11节取消后迟到资金的正向生产/ALREADY_RELEASED认证尚未启用，按D27保留能力限制：关后付款原渠道拒绝，窗口内已付/A取消只验证安全隔离，不伪造未付/超窗或资格。B-06交接见b05-b06-handoff.md，不能把支持范围验收等同生产可用。
