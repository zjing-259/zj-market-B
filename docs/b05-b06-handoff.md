> 最新Git归档状态（2026-10-11）：B-05.0～.6支持范围成果已提交为 `3de9404776377f778d5f6930d3c5ae6fd754bf68`，已快进合并master并原子推送；origin/b-05与origin/master已远程核验一致。当前分支b-05已关联origin/b-05。本条及过程归档记录随随后文档提交同步两分支；下文旧HEAD、未提交／未合并／未推送等保留各次实施时点，不代表最新状态。验收摘要中的基线和包指纹保持原始证据；B-06尚未实施。

# B-05 → B-06 交接

2026-10-11收口：B-05.0～.6在当前支持的模拟渠道范围内完成验收；取消后异常收款正向自动资格未开放，明确限制见第5节。最终总批b056-20261011-01与名额只读quota01通过，文档收口归档target/b05-joint/b056-20261011-delivery-02/report.json，106项JUnit/前端及全部本批验收通过。实际工作树D:/Java/zj-market-b-05、b-05/53ad32d，全部B05阶段变更未提交/合并/推送。Git与最新顶部状态优先于旧历史记录。B-06未开始，本交接不授权自动部署或操作外部服务。

## 1. 事实入口与可复现证据

唯一过程见[b05-development.md第15节](b05-development.md)，推荐方案总表见[路线图23.2/23.14](development-roadmap.md)，上阶段交接见[b04-b05-handoff.md](b04-b05-handoff.md)。最新六操作HTTP见[b05-http-api.json](b05-http-api.json)。跟踪摘要为[联合验收摘要](tests/b05-joint-acceptance.json)，列明实际包/原始证据hash/覆盖范围/限制；本机target仅供追溯，不随Git复制，不把旧报告当新环境验收。

统一新批次入口（显式JDK21，保留终端/A默认Java8；需要本机忽略目录凭据/证书/依赖）:

```powershell
./docs/tests/run-b05-joint.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName b056-<新批次>
```

最终verification SHA256=B8245AE51B3085CCFE9A0112467287211D777B276DEC5C9E4EAE4EAE979EF28B，普通exec=B17DED82736AD7435814A247360BAB7C86C525979FCCF4A6EAB08688DCA5CFEC。

该入口构建一次后顺序运行核对SQL、退款/同步/释放SQL、实际B HTTP浏览器、实际A无人付款、部分付款停机闭环及全付款最后事件竞争、原关单/结算/履约回归、只读审计和普通默认启动。禁止并行写库套件或重用RunName；SkipBuild需先核对同包hash。失败批次原样保留，不覆盖为通过。浏览器须实际Edge/Web Locks/锁定Playwright依赖；临时测试令牌用完删除精确browser-private.json，不提交.local、私钥、密码或登录回执。

## 2. 已实现职责与不可破坏的事实

- 完整核对任务/冻结名单/逐单事实与唯一原completionId；丢响应查原请求并重放，UNKNOWN/缺成员/身份冲突不局部提交。每成员短事务，网络在事务外；COMPLETED只清本任务临时阻断，沿原CONFIRM/PENDING。
- 稳定全额refundId、独立模拟退款根/多次尝试、明确FAILED自动退避新尝试、UNKNOWN原attempt查询；资金成功及原支付paidAt/hash不可回退。连续5次失败告警继续恢复。
- 冻结业务版本/原子Outbox及旧缺失版本追补，原事件字节不变；严格签名结果和认证Event.query+typed Trade.query，高水位不降，Broker ACK不是A接受。
- 可信全额资金与不履约资格有效才原子RELEASE/唯一流水/订单关闭/仅本单guard/原义务；A暂不可用不是前置，明确矛盾保守隔离；重复验证证明不再增库存，绝不清后来guard或回退CONFIRMED/sold/PENDING。
- 本人退款独立摘要、运营退款/核对查询、仅查询CHECK及明确失败RETRY；角色/归属/并发版本校验，actor+operationId原请求/响应审计；读页面不推进工作，丢响应沿原body恢复。

## 3. 数据库、装配与发布顺序

双B库当前V18、runtime48张业务表精确SELECT/INSERT/UPDATE/DELETE，无DDL/Flyway历史/A/system/grant。V1～V18（含V10_1）已应用、不得改写；后续新迁移追加。V14核对/义务六表，V15独立退款五表，V16Outbox/同步增量，V17释放与运营审计两表，V18CHECK原计划。普通exec不包含Flyway/verification；通过外部迁移账号显式provision，schema及精确权限验证后才启能力。禁止用清表/改paidAt/重写原证据/人工删HELD或guard来“修复”。

普通入口scripts/start-market.ps1，配置说明[b-startup.md](b-startup.md)。b.reconciliation.enabled和b.refund.enabled默认false控制新发现/新接管；各recovery-enabled默认true、scheduler-enabled默认true，仍要求原DB/order/trade/events/RPC及schema依赖就绪。CHECK/RETRY执行还需退款恢复装配，订单只读接口独立装配。checkout=false不能终止已承担任务；整个recovery/scheduler关停会暂停恢复，不能宣称同步或收尾已完成。普通无外部配置启动不主动连DB/RPC/MQ，不自动迁移。

B-06至少先验证：迁移账号/运行账号分离、schema指纹、身份密钥/来源/cookie配置、source/channel/producer与消费组、RPC客户端证书/信任链、MQ权限/可达性、数据库时钟及持久卷、退款与核对退避/租约参数、进程停止与旧任务新进程恢复。安全材料只外部注入，不放Git或普通HTTP。部署拓扑与跨主机TLS范围在B-06明确，不拿本轮单机联调替代。

## 4. 恢复与运营处理边界

先以稳定order/payment/refund/team/task和原操作ID定位；分别查看资金、A同步、库存状态及原失败码/告警，不能把“退款成功/ACCEPTED/work DONE”混为全部收尾。先查询原渠道/原事件，响应不确定保持原键；明确FAILED且资格有效时才RETRY。暂不可用恢复原任务，不新造金额/事件/attempt；同版本异事实/非法绑定保留隔离及证据。

REVIEW不是可强制通过的运营按钮。当前运营只提供查询与有条件重试，不提供修改证明/强制退款/手工释放或通用解除隔离；真正矛盾须诊断、修复来源并单独设计受控恢复与审计。系统启动时schema不满足应拒绝相关能力；异常计数是累计隔离测试库统计，不能当作本批失败数或生产待退款金额。

## 5. 明确限制与B-06待办

1. 当前自动执行资格为TEAM_FAILED_ACCEPTED、OUTSIDE_WINDOW_RESOLVED。CANCELLED_LATE_PAYMENT正向资格生产未开放：普通模拟渠道根关闭后禁止收款，受控A取消而窗口内渠道已付只验证安全隔离，保留资金/HELD/guard，不伪称超窗或未付。ALREADY_RELEASED有严格原未付证明核验分支，但没有正向异常渠道生产闭环认证；若未来渠道可能关后收款，必须独立扩展证明、恢复与专项验收。这是明确能力限制，不能宣称完整真实渠道覆盖。
2. 本轮是真实MySQL、独立模拟资金、实际A/TLS/签名MQ及受控故障；不涉及第三方真实资金、部分退款、主动退团、逆向履约或发货。跨主机/中间件断电/持久卷丢失、生产证书与容量、监控/告警路由/备份恢复/发布回滚归B-06。
3. 部署后需重新验收自己的配置与新团队，不复用本机.local或旧超时订单。应用回滚不得降到不认识V14～V18的旧执行器继续处理资金；数据库备份与回滚演练须保留原渠道/商城/Outbox/租约和业务审计一致性。具体部署、监控、备份脚本尚未实现。
4. B05成果未提交；提交/合并/推送必须由用户另行授权。外部A50051及共享MySQL/Redis/MQ不属于本轮自有进程，不能停止或重建；A外部并行修改保持。
