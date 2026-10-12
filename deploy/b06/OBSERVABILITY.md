# B-06.4 轻量观测运行手册（Windows Docker）

仅操作zj-market-b06。工具不提供新的HTTP入口，正常观测不使用root、不发消息、不消费/重置MQ偏移、不改支付/退款/库存。明确初始化账号时才使用已有维护权限；默认Docker context保持原值，所有调用显式desktop-linux。Linux尚未验收。

## 开始与停止观测

在b-06工作树根目录、独立PowerShell窗口执行：

```powershell
Set-Location D:/Java/zj-market-b-06
python -B scripts/b06-observability.py init
python -B scripts/b06-observability.py once
python -B scripts/b06-observability.py watch --interval 30
```

init只创建/核对专用b06_observer账号及26张精确业务表SELECT权限，REQUIRE SSL，不读取身份表、迁移历史或mysql系统表，无DML/DDL/授予权限；未知既有账号拒绝接管，重复init不换密码。Windows观测目录仅当前用户/SYSTEM/Administrators可访问。普通采集是96MiB、0.5CPU、64进程上限的非root临时MySQL客户端，挂载单独凭证和MySQL CA；临时复制配置chmod600，避免Windows挂载权限使客户端忽略密码文件。主机名mysql、VERIFY_IDENTITY、实际TLS cipher均验证。

watch是前台循环，采集结束后等待30秒，允许10～60秒；Ctrl+C正常停止，后台资金恢复服务继续。工具未自动注册开机任务，也没有隐含常驻进程；重启电脑后须再次启动watch。一次只能一个采集/trace/init；并发调用立即失败，不重复写告警。status不取业务数据，可在另一个窗口执行：

```powershell
python -B scripts/b06-observability.py status
```

心跳超过90秒、时钟回拨、采集不完整或存在活动告警时返回非零（2），不能把昨天快照当当前健康。once完成只表示本次采集/健康成功，业务告警另看status；快照/健康不代替受控业务准入。停止watch时无法主动记录后续故障，更不能发送外部通知；status会显示过期UNKNOWN。当前交付已完成实测，未自动启动长期watch。

## 私有结果与口径

.local/b06/observability/latest.json为当前快照；samples.jsonl为结构化观测日志，alerts.jsonl为本地告警事件，alerts-state.json为状态，last-trace.json及traces.jsonl为关联查询。三类JSONL分别按2MiB轮转、保留当前和3份历史；单条大小会造成少量超限。最新快照/告警状态文件原子替换，告警先持久化意图再追加，进程中断可按相同incidentId重放；查询端按incidentId及event去重。不是外部通知/告警服务器，旧轮转事件也不是无限审计归档。.local全部不进Git。principal.json/mysql.cnf含专用凭证，不分享这些文件或整个.local目录。

| 指标 | 精确含义 |
| --- | --- |
| health | 七服务running/健康/OOM/重启次数；网关严格HTTPS；数据库严格TLS实际查询。A/B是HTTP进程存活，MQ是TCP存活，Redis为既有认证PING；不能冒称RPC/MQ消费就绪 |
| pending / due | 当前非终态数量；非隔离且next_attempt已到期数量，未来调度不计due；租约有效与否另列，due不保证立即可领 |
| oldestPendingSeconds / oldestOverdueSeconds | 同一只读一致性事务内以数据库毫秒时间计算；无创建时间的A等待表年龄为null且ageAvailable=false；没有到期记录时overdue为0 |
| recordedFailures | B各记录当前failure_count或商品send_failures之和，可重置，不是永远递增的累计指标；A没有对应失败字段则为null |
| recordedRetries / recordedDependencyChecks | A Outbox的max(attempts-1,0)之和，首次发送不算重试；A依赖检查次数单独呈现，不叫失败 |
| review / expiredLeases | 队列REVIEW_REQUIRED或暂停数量；非终态已过期租约数量，终态旧租约不计；不能直接删除/解租约 |
| funds obligations | 成功支付尚待A、退款资金/同步/释放任一步未完成及最老等待时间；原持久任务和权威状态共同定位 |
| historicalClosedRefundReview / historicalClosedUnpaidReview | 按D31/D35证据区分保留审核的全退关闭/未曝光关闭历史；活动订单/支付审核、非核对ACTIVE阻断另列并告警，不清理原标记 |
| quarantine receipts / pendingFulfillment | 历史隔离收据与未重放商品收据、待履约数量；B-06没有发货功能，PENDING履约不是恢复失败；隔离收据无处理终态的表不能凭总数断言当前隔离任务 |

固定12队列：B支付、订单协调、贸易工作/Inbox/Outbox、模拟付款通知、完整核对、退款、模拟退款通知、商品Outbox；A Outbox及等待依赖。指标标签仅固定队列/服务，无订单ID高基数标签。broker消费lag未采集，绝不能以容器健康或Inbox行数替代broker lag。

默认本地告警：服务/HTTPS不健康、数据库采集UNKNOWN、活动审核/非核对阻断为CRITICAL；到期积压超过300秒、支付待A/退款未完超过300秒为WARNING。重复相同状态不重复触发；恢复记录相同incidentId。数据库采集失败保留queues/obligations=null和已有业务告警，不解除或填0；恢复成功后才重新判断。历史隔离收据不作永久活动故障，新收据须结合工作/运营入口定位原因。

B063中断批保留两条无到期工作的Inbox历史WAITING_DEPENDENCY记录，快照会显示pending/老年龄但due=0；这是可见状态，不是本轮自动修复权限，不篡改其next_attempt。当前三条已全退关闭审核、一条未曝光关闭审核单列为历史，既有TEAM_FAILED投影保留。运营如见资金任务REVIEW_REQUIRED、非核对阻断或缺证明，应使用原受控恢复流程，不能为消告警直接改数据库状态。

## 业务关联与日志查询

```powershell
python -B scripts/b06-observability.py trace --kind order --id <orderId>
python -B scripts/b06-observability.py trace --kind payment --id <paymentId>
python -B scripts/b06-observability.py trace --kind refund --id <refundId>
python -B scripts/b06-observability.py trace --kind team --id <teamId>
python -B scripts/b06-observability.py trace --kind event --id <tradeOutboxEventId>
python -B scripts/b06-observability.py trace --kind task --id <taskId>
```

查询只接受1～64位ASCII业务ID，最多100行/5秒SELECT。task支持贸易workId、完整核对taskId、支付/退款根任务ID；event当前支持B贸易Outbox eventId，不宣称可自动解析任意原始消息。输出仅允许标量状态/金额/时间及work/event ID，显示B付款/A接受、退款资金/同步/释放、A当前团队与历史paid计数、库存账户/预占和CONFIRM/RELEASE流水数量。不输出userId、快照、消息正文、签名、cookie、请求或证明。没有匹配时为空，不能据此判定资金不存在；进一步使用原运营只读页。库存账户是商品总余额，不是本订单独占余额。

B部署启用Spring Boot ECS JSON，请求记录http_request_completed，字段requestId、固定MVC route模板、method、status、durationMs。响应X-Request-Id用于连接B和网关http_access日志；网关只记requestId/status/duration，不记query、原始URI、header/body。普通上游错误用JSON访问状态记录，Nginx错误级别收紧至crit以避免普通上游错误回显URI。原A冻结包日志及部分库/System.err输出仍是原格式，不能说所有第三方日志均改成JSON。敏感值不得放URL；本轮成功/校验失败/身份失败/404/上游502的标记及实际运行密码均实测未落B/网关日志。

```powershell
docker --context desktop-linux logs --since 10m zj-market-b06-market-b-1
docker --context desktop-linux logs --since 10m zj-market-b06-web-1
```

仅在本机按响应requestId筛选，不外发整段日志。Docker七服务json-file沿用10MiB×3；RocketMQ原生日志卷仍按服务自身配置管理，stdout预算不等于卷总占用。A关联依靠原业务ID和只读投影，不重编脏A源码。Boot ECS配置依据[官方结构化日志文档](https://docs.spring.io/spring-boot/reference/features/logging.html#features.logging.structured)。

## 故障定位和恢复

先status看新鲜度，确认watch在运行；UNKNOWN时核对Docker引擎、zj-market-b06容器归属、数据库TLS/观测账号权限，不把缺数当恢复。普通日志不输出驱动原始异常/凭证；维护者可执行原b06-deployment.py ready复核schema/Flyway/运行权限/迁移锁定，但这不是每30秒使用root的观测方式。

健康恢复只恢复原项目容器/配置；资金及A同步问题先trace/运营页查看原工作、资格、渠道事实与库存，再走原暂停/恢复/核对入口。不得改paidAt、伪造退款、清队列/卷、重置broker偏移或批量消除review。历史TEAM_FAILED与真实隔离要按完整证据区分。

新批次验收须独占演示环境且库存无预占；会短暂停止本项目B和网关，并只撤销/恢复观测账号一张表读权限。finally恢复原服务/读权限，任何失败先核对实际状态，不重跑B062要求无支付/退款的旧脚本。验证用派生SELECT行测队列语义，绝不向真实资金队列植入测试任务：

```powershell
python -B docs/tests/test-b06-observability.py
python -B docs/tests/run-b06-observability.py --run-name b064-<fresh-name>
```

最终b064-20261012-03：39项真实检查、7项工具测试、109项应用测试、33项普通镜像/9项维护镜像一致性通过；摘要docs/tests/b06-observability-acceptance.json，发布指纹docs/b06-observability-release.json。B/网关升级加载，A镜像不变；资金/库存/团队指纹、共享容器、hosts保持。七服务健康、open/READY，无活动本地告警。前两失败批保留：01未识别从未曝光且已关闭的历史审核，02错误期望非法query返回200且误判ECS字段为平铺；实际接口400、ECS为嵌套对象，修正验收后以新批03完成，不改旧批为PASSED。


2026-10-12最新收口：B06.5当前候选07的112项矩阵及NameServer recovery-03、B缺失runtime-gap-02均通过，全部逆操作已收口；原暂停/旧候选/失败批为历史，不覆盖。B缺失仍需手册的受控open再recover两步。七服务open/READY，无活动告警；最新发布/验收见docs/b06-fault-release.json、docs/tests/b06-fault-acceptance.json。

B06-D44（采用推荐，最终观测补修）：修复通知解析后，一条TEAM_FAILED原消息晚于同团队RESOLVED及本订单全额退款/A同步/库存释放到达，原接收器合法保留DEFERRED_B05交接行，发现器不会重建已有核对任务。它不是仍待退款的义务；旧只读观测把next_attempt_ms=0视作从纪元起积压，最终汇总因真实活动告警拒绝。保持原行、原调度和原证据，不SQL清DONE、不清告警、不扩大自动重放。仅把严格绑定且已全部收尾的TEAM_FAILED/TEAM_RECONCILIATION_REQUIRED交接行单列historicalSettledHandoffs：必须DEFERRED_B05、无租约、原evidence hash一致、原source/channel/team与订单和RESOLVED任务一致，订单CLOSED、付款SUCCEEDED/ACCEPTED、同payment全额退款SUCCEEDED/ACCEPTED/RELEASED、预占RELEASED、恰一RELEASE且无CONFIRM/履约/非核对ACTIVE阻断或REVIEW工作。任一缺证或矛盾仍计活动，REFUND_OBLIGATION不走此分类，原审核/隔离/资金投影保持。实现只涉及外部SELECT-only/TLS观测脚本，不修改镜像、权限、迁移或资金规则。

D44验证：新增3项隔离关系测试执行同一SQL谓词，覆盖两类有效交接及30个缺证/错误绑定/活跃租约/未同步/金额不全/重复释放/确认或履约/审核等反例；7项原观测与9项故障工具回归通过。真实MySQL原观测账号查询通过，BLOB证据按UTF-8显式转换后读取JSON；第一次缺少转换的SQL验证返回UNKNOWN并保留诊断，不冒称成功。最终历史交接1、活动trade-work 0、所有资金义务/库存预占/活动审核0，原backlog:b_trade_work同incident恢复，无活动告警。未删除原交接、隔离或审核记录。该补修在07业务矩阵与两项恢复之后完成，只读真实终态再次汇总通过，不伪称07每一历史采样使用了新口径；最新observer/测试hash及补充验证见tests/b06-fault-acceptance.json的observerHistoryClassification，原业务源码/普通镜像未变，无需重跑资金矩阵或镜像构建。
