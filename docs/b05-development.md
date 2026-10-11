> 当前状态（2026-10-11）：B-05.4可信退款事实与A同步已实现并通过同包业务验收；b-05/53ad32d，阶段变更未提交/合并/推送。双B库V16/runtime46表精确DML；103项JUnit、SQL03/跨JVM、实际A live-02停启/签名MQ/严格查询/新B进程、关单/结算/履约回归及普通启动通过。推荐D18～D20已保存双路线图；最终归档见target/refund/b054-20261011-delivery-02/report.json，过程见[b05-development.md第13.2节](b05-development.md)。付费HELD/guard保留；库存释放/HTTP/页面归.5、完整联合矩阵归.6。A外部并行改动保持，实际验收A包及契约不变。下列旧状态保留历史时点。

# B-05开发过程：到期核对、失败退款与恢复

更新：2026-10-10（Asia/Shanghai）。工作树：`D:/Java/zj-market-b-05`；分支：`b-05`；创建基线：`53ad32d222cdcb1b330cf07a53b2fd64e02ccccf`。

本文件为B-05唯一开发过程文档。后续每次B-05工作同时维护本文件和[development-roadmap.md](development-roadmap.md)：详细决策、实现、接口、迁移、测试和遗留集中于本文件，路线图维护整体状态与依赖；接续入口同步[session-handoff.md](session-handoff.md)。不根据历史对话假设修改已落地，以实际Git、源码与最新持久化文档为准。

## 1. 当前授权与状态

工作树和阶段入口已建立；B-05前置规划及三项用户选择已确认，B-05.0基线与环境接续已完成，见第8节。B-05.1联合设计已完成，见第10节；.2～.6实现/验收及B-06待开展。未实现退款/核对执行器、未修改A契约；第8节的.0曾显式校验既有迁移并运行隔离验收服务，没有新增迁移；本轮.1仅设计及静态检查。本阶段文档与验收入口改动尚未提交、合并或推送；后续是否提交按新的授权执行。

2026-10-10创建前已fetch origin：master、origin/master及b-04均为53ad32d，本地主工作树干净；本地及远端均未发现b-05。从master创建本地b-05及D:/Java/zj-market-b-05，创建后HEAD核验53ad32d，工作树初始干净。新分支尚无远程上游，不把本地创建当已发布。B-04开发提交1b5242e及发布文档53ad32d均已在基线内；其历史“未提交”等表述只代表当时状态。

新工作树只包含Git归档文件；旧工作树忽略的.local凭据、target报告/JAR、node_modules不会自动复制。B-04历史验收不是新工作树环境验收。后续环境接续须显式核对，凭据仅保存在忽略位置，不清除原数据库样本、不打印密钥。

## 2. 接续事实与约束

权威接续：[B-04→B-05交接](b04-b05-handoff.md)、[B-04过程](b04-development.md)、[A权威契约](../../group-buy-market/docs/ab-api-contract.md)、路线图B-05范围。基线包含B-04.0～.6与模拟通知ACK/重试锁后取时补修；历史完整联合验收和补修专项证据各按B-04第15/16节解释，不合并声称新包全矩阵通过。

- 已有独立持久模拟渠道、稳定paymentId/多attemptId、原资金事实与支付Outbox、签名结果、根未付关闭证明、成团CONFIRM/PENDING。资金仅模拟，退款执行尚未实现。
- TEAM_FAILED、TEAM_RECONCILIATION_REQUIRED及REFUND_OBLIGATION已持久接收。DEFERRED_B05/Inbox DONE不是退款或核对完成，旧工作证据、UNKNOWN、HELD及guard必须保留。
- 稳定refundId已由A协议确定；核对completionId单独稳定。退款全额、后台驱动；UNKNOWN查原键不换业务标识。全额退款成功并完成库存释放后解除本单guard，不伪造CLOSED_UNPAID或回滚已售库存。
- 完整核对用queryReconciliation/completeReconciliation RPC及逐单Trade.query，名单不全、资金未知、冲突继续等待/核对。A退款消息仅PENDING/FAILED/SUCCEEDED及单调refundVersion，内部UNKNOWN不能直接上报。
- 网络和独立渠道调用在商城事务外；遵循既有业务锁序，新增退款锁位置先设计。工作写回先锁行再读数据库时间，核对intent/token/lease；失效处理者无权提交。
- 迁移从V14开始，旧V1～V13（含V10.1）不改写；基线runtime精确35表DML、普通包无Flyway。普通payment/checkout/events仍默认false。

## 3. 后续实施顺序与待决问题

以下为待细化计划，不代表已批准的详细方案或已完成子阶段：

1. 基线与环境接续：阅读最新docs/源码和A契约，核对配置/依赖/旧接管样本，以新批次验证环境与只读接管安全。
2. 联合设计：冻结完整名单核对、停止支付、稳定核对请求、退款业务与渠道尝试、锁序、状态及恢复/故障矩阵；向用户提出影响业务或运营的方案问题。
3. 到期核对：完整名单与逐单资金证据、原completionId请求恢复、未知/缺依赖可见等待。
4. 独立模拟退款与可信通知：原成功资金绑定、全额限额、原refundId恢复、退款事实与原Outbox原子提交、A严格结果验证。
5. 退款后收尾与运营恢复：唯一RELEASE、库存/订单/guard/工作同事务；最小可审计查询/重试权限及告警。
6. 联合故障验收与B-06交接：真实A/MySQL/MQ、独立渠道、跨进程及受影响成功链路回归；分别标注实际/受控/模拟证据。

第3节为初始化时的概略计划；退款自动退避、运营页面及verification故障隔离已按第6节B05-D1～D3确认，.1继续细化内部尝试/状态/权限等实现。已有D1～D7、稳定refundId和UNKNOWN原键恢复不重复询问。不得提前用本次建文档替用户确定新业务方案。

整体复杂度高：资金核对、独立退款、可靠消息和库存收尾存在并发与故障依赖；本次工作树/文档初始化复杂度低，未实现业务。

## 4. 验收与风险记录规则

每次工作记录目标/实际改动/决策/测试命令与结果/证据目录/失败与剩余项；报告使用新批次，保留失败、原始消息及资金事实。覆盖完整名单和版本缺口、缺本地成员、全部/部分付款终局、退款提交前后崩溃、响应/通知/ACK丢失、唯一义务与不超额、旧支付/关单竞争、过期租约/替换令牌、新进程恢复、唯一释放及后来guard安全。

B-04只读交接审计当前把成功/UNKNOWN资金已释放视为违规；B-05实现合法退款后须扩展审计为验证可信全额退款、终局和唯一RELEASE，不能直接删除安全检查。实际A、模拟渠道、故障工具和浏览器分别注明来源，不声称真实第三方扣退款或生产部署已验收。

## 5. 本次初始化记录

2026-10-10：已完成分支/工作树创建、新建本文件、路线图及接续入口更新。核验Git分支/HEAD、文档相对链接及差异空白；仅文档变更，无业务测试或迁移。原master/b-04工作树与A保持不变。B-05业务待开展。

## 6. B-05前置及阶段规划（2026-10-10）

用户指定在当前b-05工作树规划，并同步主目录路线图。实际目录为D:/Java/zj-market-b-05，基线53ad32d；不新建相近拼写的目录。阶段与验收门槛统一见[路线图第23节](development-roadmap.md#23-b-05前置与分阶段实施规划)。本轮未实施业务、复制凭据、运行测试/迁移、提交或推送。

本轮确认：B05-D1明确退款失败自动退避，连续失败告警后继续恢复；UNKNOWN查原尝试，稳定refundId不变。B05-D2异常列表/详情及查单、受控重试页面，复用现有运营权限并审计，不强制成功/释放。B05-D3正常模拟退款自动成功，故障仅verification注入，普通/运营页面不增加故障控制。三项均来自用户本轮回答，没有未答选择；既定全额、后台驱动及退款成功后释放/解除guard规则保持。

实施顺序：B-05.0基线与新环境→.1核对退款联合设计→.2完整到期核对→.3独立模拟退款→.4退款事实及A可靠同步→.5原子库存收尾和运营页面→.6联合故障及B-06交接。第6节规划收口时.0已完成、.1～.6待开展；最新.1已完成设计，.2～.6待开展。原第3节为概略顺序，以此编号和路线图门槛接续。

.1须重点解决：.2先持久退款义务/refundId供超窗核对，不等退款完成；现有支付Outbox唯一约束如何兼容退款多版本；区分正常核对临时阻断与真正证据冲突；退款尝试/锁序/状态/接口及V14起迁移。原A契约沿用，若有真实差异先解释并提方案，不直接改A。规划时环境复验与新样本待.0；现已按第8节完成，独立证据不与旧工作树混用。

## 7. 本次任务复杂度评估

规划维护复杂度中等，实施复杂度高：完整核对、独立资金退款、可靠消息与库存收尾涉及多个事务和故障恢复。按路线图第23.3节七阶段推进，各有依赖/验收；高复杂度部分再拆为.1状态/键/锁序/表接口/矩阵，.2名单/成员事实/冻结提交/恢复，.3渠道意图/退款/通知/未知恢复，.4版本事件/回执/补查，.5原子释放/重放保护/运营页面，.6故障/回归/守恒/交接。规划时下一步为.0；当前.0完成，下一步.1联合设计，未自动进入业务编码。

## 8. B-05.0基线与环境接续（已完成）

2026-10-10授权开展.0。实际b-05/53ad32d，保留前轮规划及B05-D1～D3；主目录路线图已有前轮规划差异，按操作前状态/内容指纹保护，不误称主目录干净或覆盖它。未发现AGENTS.md额外规则。

计划：接续两份同机DPAPI数据库凭据及测试公私钥（仅忽略.local，不覆盖已有文件）；显式JDK21构建与锁文件前端构建；普通包隔离与真实启动；复用真实A/readiness验证双B库V13/35表权限、RPC/TLS/MQ和新B三人成团样本；专项资金/通知租约/新JVM恢复；只读交接快照及旧work证据/UNKNOWN成功资金/HELD/guard/原渠道成功保护；最终证据/交付审计与文档。网络/资金业务方案不在.0新增，无新待决问题。

新增串行入口docs/tests/run-b05-baseline.ps1，报告target/b05-baseline/<RunName>/report.json，拒绝覆盖旧批次/占用端口。显式迁移校验及权限临时DDL会运行，不称全程只读；受控资金与真实A样本分开，旧库不清理，.1核对/退款业务仍未实现。当前Docker/MySQL/Redis/MQ已运行，不停止共享服务。

### 8.1 首轮证据归档失败与修正

b050-20261010-01完成77项测试/前端/普通启动、双库/真实A三人成团、资金和通知六组及新JVM、接管六项零违规；1424条旧保护记录缺失/改变为0，环境/Java/端口/其他工作树检查均通过。但新增Save-Report以原始路径字符串比较，混合斜杠未规范化，复制同一个delivery-audit.json时失败，总报告保持FAILED。修正为GetFullPath比较并留存异常类型，普通启动显式关闭payment/events；不修改业务代码、数据或首轮证据。另起b050-20261010-02完整复跑，不将首轮业务通过冒充总入口通过。

### 8.2 最终新批次与验收结果

最终批次target/b05-baseline/b050-20261010-02/report.json为PASSED，首轮01的FAILED报告和所有样本保留。新增的只有串行验收入口及文档，没有修改业务Java/HTTP/A契约或旧迁移。复验使用本工作树独立构建的同一包，起止校验JAR、依赖锁文件、A契约/包及全部迁移指纹；新构建不能用B-04历史SHA冒充。

| 范围 | 本批结果与证据 |
| --- | --- |
| 构建/前端 | build.log：七模块、77项JUnit零失败/错误/跳过；frontend.log：npm ci、vue-tsc/Vite构建；Node24.16.0/npm11.13.0，锁文件保持 |
| 普通启动/依赖 | normal-runtime.log：JDK21.0.2实际普通入口启动；普通exec无verification/Flyway；A/B包中的Java8契约JAR指纹相同 |
| 双库/权限 | 两组database凭据-migrate/verify.txt及migration-history.txt：开发zj_market与隔离zj_market_b02_test均V13、14条成功SQL历史（含10.1）、本轮新增迁移0，runtime精确35表DML，DDL/history/A/system/grant拒绝；显式迁移校验/临时DDL不称全程只读 |
| 真实A/RPC/MQ | target/b03-readiness/b050-20261010-02-live与底层environment-probe：A Java8、B Java21、TLS有效签名/无效签名拒绝、MQ ACL收发与越权拒绝、原结果持久查询；新用户/运营/商品版本同步、报价/占位/满团/期限/资格/关闭标记及新B进程原请求恢复 |
| 完整成功链路 | live/fulfillment.json与txt：新3笔完整B订单、独立模拟付款、真实签名支付及成团MQ、TLS逐单完整资金查询、3唯一CONFIRM/3 PENDING；库存available6/reserved1/sold3，另一订单仍HELD，本人HTTP/异主404通过 |
| 资金/通知恢复 | target/settlement/b050-20261010-02-settlement：资金/Outbox原子回滚、并发幂等、严格签名/冲突隔离、D6缺订单/唯一退款义务、真实期限后首次观察原paidAt、A离线/新JVM丢ACK恢复；通知ACK/REVIEW ACK/retry真实行锁跨租约及令牌替换六组通过 |
| 接管/旧样本 | handoff.json：六项违规均0，保留DEFERRED_B05/缺本地/异常；before/after-protected.txt保护原work原文/hash、成功/UNKNOWN资金、HELD、guard及原渠道事实，原记录缺失/改变为0 |
| 收尾/交付 | 环境恢复、默认Java8不变、自有50051/18091/18092/5173释放，其他工作树HEAD/差异/主路线图原内容保持；共享中间件不停止。delivery-audit.json敏感值/完整私钥/令牌零命中，已跟踪忽略文件0 |

本批旧保护记录1463条，结束1502条，原记录缺失或改变0条。累计快照缺本地工作43项、PENDING 29项；这些含历次真实A/受控样本，不是生产待处理数。

本批包指纹：

- zj-market-app/target/zj-market-app-exec.jar：`CA135A6297618E692E3D58C31CCA22D9A237B01B0017B8C7685CA0438CDB1C23`

- zj-market-verification/target/zj-market-verification.jar：`7CFA0A3772F5E153D79718AB587A53A60FAD0E043408AA9D453832DD1023F9E1`

### 8.3 接续清单与复现

本工作树已具备被忽略的两份DPAPI数据库角色凭据及测试签名公私钥；A配置继续从原A的.local外部读取，没有复制旧账号批次/target报告，不改全局JAVA_HOME。B05-D1～D3沿用，无本轮新增待答方案；.1仍需按第6节重点完成核对/退款联合设计。

新实际样本以live/fixtures.json、live-fixtures.json、fulfillment.json及忽略的.local/b03-b050-20261010-02-live.credentials.xml映射；完成订单已PENDING，不作为后续到期失败样本复用。未来.2/.6须创建新B完整团队，核对活动target与数据库截止，不续期、拼旧直接A记录或清历史资金/库存。模拟渠道回归与真实A成功链路证据分开，不宣称已验退款、到期完整核对、真实第三方资金、浏览器或部署。

```powershell
./docs/tests/run-b05-baseline.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <全新批次>
```

入口需要本机已有Docker/MySQL/Redis/RocketMQ、Java8 A包/外部配置、JDK21、Maven及Node；CredentialSource可指定具备同机DPAPI记录的可信旧B工作树，默认b-04。已存在的本地文件不覆盖，凭据只在忽略目录，provision不清库；每次运行都会显式验证/生成独立样本并留存报告，不适用生产。前端/普通包/真实A/资金/快照按串行顺序运行。

当前b-05/53ad32d，所有本阶段文档和入口尚未提交/合并/推送；主B原规划差异、b-04与A均保持操作前状态。本轮复杂度中等，四步已收口；B-05整体仍高复杂度。下一步B-05.1，.2～.6及B-06未开发，不自动启用普通资金入口。

## 9. 开发方案选择同步路线图（2026-10-10）

用户要求B-04及B-05开发中出现的方案选择同时写入development-roadmap.md。已对照B-04过程第4/10节和本文件第6节，路线图20.2集中完整B04-D1～D7；23.2维护B05-D1～D3，记录确认日期/来源、结果、影响及落实状态。详细讨论、实现和证据仍归各阶段过程，不把已确认选择重复列为待答或将技术细节冒充新用户选择。

路线图第5节新增持续维护规则：后续每次提出或确认/改变方案，两份文档同步，保留编号及历史替代关系。同步当前工作树与主目录路线图的决策表和该规则，主目录其他规划差异保持；未同步业务源码或本阶段全部进度。B-05.0仍已完成，.1～.6待开展。本次只维护文档，检查选择编号/内容一致、相对链接和历史SHA保留及差异空白，不重跑业务测试，未提交/合并/推送。


## 10. B-05.1核对与退款联合设计（2026-10-10，设计完成）

用户授权开展.1，方案选择采用推荐并同步路线图，B04相关以b04-b05-handoff.md接续。先核对最新docs/Git/A契约和实际代码，不假设旧聊天落地；b-05/53ad32d及.0既有未提交修改保留。实施计划：①事实/契约差距；②状态、键、事务/锁序；③迁移/消息/HTTP；④故障矩阵及静态验证。不开展.2～.5执行器编码。

### 10.1 交付与已选方案

详细领域规则集中于[b05-joint-design.md](b05-joint-design.md)12节；增量接口[b05-http-api.json](b05-http-api.json)6操作，明确design-only；CONTEXT.md增补核对/名单/提交/义务/退款单/尝试/成功术语。D1～D3沿用，新增D4～D11按用户授权推荐决定，已同步本工作树及主目录路线图23.2。主目录仅插入本轮新决策/链接，其原规划差异与其他字节保持，不复制整个实施进度。

| 编号 | 推荐方案（用户授权确定） | 关键影响与约束 | 来源／落实状态 |
| --- | --- | --- | --- |
| B05-D4 | 稳定退款单下多渠道尝试 | 全额refundId绑定原订单/支付不变；明确FAILED才新attempt，UNKNOWN原attempt；渠道原支付根锁防超额 | 2026-10-10用户授权按推荐确定；.1设计已选、待.3实现 |
| B05-D5 | 完整名单与唯一冻结核对提交 | 先建退款义务支持超窗核对；completionId/checkedAt/原请求不可变，冻结后不自动换ID绕冲突 | 2026-10-10用户授权按推荐确定；.1设计已选、待.2实现 |
| B05-D6 | 有归属的临时阻断与冲突分离 | 正常核对可继续原键查单/关闭；可信成团只解除本任务阻断，旧原因不明review保守保留 | 2026-10-10用户授权按推荐确定；.1设计已选、待.2/.5实现 |
| B05-D7 | 原交易Outbox扩展退款多版本 | 保留支付唯一键；增加退款复合绑定/CHECK及严格结果分支，旧回执返回新版本须匹配已持久事实 | 2026-10-10用户授权按推荐确定；.1设计已选、待.4实现 |
| B05-D8 | 退款资金、A同步、库存收尾独立 | 有权威不履约依据且可信全额成功才原子释放；无需等A退款ACK；已释放异常收款不二次加库存/清新guard | 2026-10-10用户授权按推荐确定；.1设计已选、待.3～.5实现 |
| B05-D9 | 运营控制只用CHECK与受控RETRY | 复用OPERATOR；actor/operationId幂等、expectedVersion及审计；无强制成功/释放/改资金 | 2026-10-10用户授权按推荐确定；.1设计已选、待.5实现 |
| B05-D10 | 持续恢复与有界退避参数 | 扫描2s/调用10s/租约30s/续租20s；2/4/8/16/30s+jitter≤250ms，5次告警仍恢复；锁后DB时间fencing | 2026-10-10用户授权按推荐确定；.1设计已选、待.2～.5实现 |
| B05-D11 | 义务与执行资格分离 | A_REJECTED只是线索；可信FAILED接受付款、核对异常已落地或CANCELLED迟到收款才执行，成团/履约矛盾隔离 | 2026-10-10用户授权按推荐确定；.1设计已选、待.2/.3/.5实现 |

义务先持久refundId供超窗核对，A终局后执行全额退款、成功后释放，消除循环等待；UNKNOWN从不换键。核对提交冻结后不自动替换，真实冲突保守隔离。临时核对block有归属，不能清真正review。退款/A同步/库存状态独立；先前已释放异常收款退款后不二次RELEASE、不清后来guard。计划V14最小名单/义务/阻断6表，V15渠道执行5表，V16扩展Outbox，V17收尾/审计2表，精确DML计划35→41→46→46→48，均未生成/执行SQL。

### 10.2 当前源码风险与契约限制

确认支付Outbox类型CHECK/固定version、退款结果被reader忽略、transport仅支付、无核对RPC适配、RECONCILING混用review、CLOSED仅未付basis，需要.2～.5逐步兼容。原Java/旧迁移/已有HTTP/A契约保持，不以新文档冒充这些缺口已修复。A V2TeamEngine及V2EventEngine代码用于核对现有契约，无A变更。

A Reservation/CloseResponse没有closeId；close重放已取消记录可能不证明使用B请求中的关闭键。设计不假造查询字段：保留本地原closeId/请求和权威CANCELLED，由A complete最终原子核验；不匹配隔离、不换ID。A处理低退款版本可返回更高当前版本，须核对本地确有相应不可变事实，再认可高水位，不把旧ACK强行等同旧版本。

### 10.3 静态验证与交付边界

新增docs/tests/validate-b05-design.py，以标准库解析增量规范、检查引用/鉴权/操作/必填字段，运行完整名单/窗口、退款未知/失败重试/超额/释放/旧回执场景，校验迁移表数、决策双文档同步、Git和受保护源码/旧迁移/已有HTTP/A契约指纹及主路线图插入外字节。独立报告target/b05-design/b051-20261010-03/report.json，01、02静态检查各142/142通过，报告保留；最终复核补充A已成团可能没有名单、查询FAILED不能证明超窗声明登记的边界，并更新B04交接入口。最终03批次144/144通过，未覆盖旧报告。

复现命令（本机Python3，需本设计批次的忽略目录before.json/main-roadmap-boundary.json作为边界证据；新批次不得覆盖）：

```powershell
python -X utf8 docs/tests/validate-b05-design.py --run-name <全新批次>
```

144项包括规范/引用/鉴权、正负接口、设计模型和边界检查，不是144项退款运行测试。检查证明本轮受保护Java/旧SQL/依赖/HTTP/A契约指纹无变化，主目录仅新增方案表、A/b-04无差异，未改变历史基线报告指纹。

本轮只做设计及静态规范检查，不启业务进程、不执行数据库迁移、不重跑.0的77项/真实A/浏览器；那些历史证据保持原样。当前仍V13/35表，普通资金入口默认关闭。未提交/合并/推送；.2～.6及B-06待开展，无未答方案。整体复杂度高，本轮按上述四步完成设计，实际并发/故障证明留给各实现阶段，下一步.2。


## 11. B-05.2 到期完整核对（2026-10-10～11，已完成）

用户授权开展.2，新增方案按推荐确定并记录路线图。计划：V14六表/41表精确DML→独立核对RPC/单成员租约→原渠道/支付Outbox/未付关闭复用及临时阻断→冻结提交/退款义务/终局恢复→构建/实际SQL/真实A及回归。旧未提交设计、A契约、旧V1～V13及原始资金/工作证据保留；退款执行归.3。名单收集每租约只处理一个成员，团队聚合不反锁订单；旧无归属review保持LEGACY，不自动清除。运行结果后续逐批补记。

### 11.1 实施及推荐选择

新增领域IReconciliationPort/Repository/Service、独立TLS签名Team/Trade RPC适配、ReconciliationRepository、OrderReviewBlocks、2秒后台恢复及配置；V14六表原子保存完整名单、逐成员证据、唯一冻结提交、退款义务、Inbox关联和阻断。双B库V14/41表精确DML已验证，旧迁移无改动。普通新核对开关默认false、已有任务恢复默认true，均以原trade.events开启和所需能力为前提；关闭调度不隐式消费或开启支付。

每成员前缀锁内停新支付/废止旧支付intent；锁外原渠道逐attempt查单、原M2补原paidAt/Outbox；未付通过既有根关闭和原A closeId/query后才形成声明。完整集合齐备冻结唯一completionId/checkedAt/业务字节/hash；丢响应查原键，即使A已FAILED仍重发原提交。FAILED接受款生成全额义务和资格，超窗先义务后原提交ACK资格；不执行退款、不发退款MQ、不释放付费HELD。COMPLETED不强求有核对名单，只解除自有临时阻断，继续原成团工作，不伪造A消息。

| 编号 | 推荐方案 | 影响与约束 | 来源／状态 |
| --- | --- | --- | --- |
| B05-D12 | 名单收集每租约一个成员，不循环持全团队订单锁 | 30秒租约内只做两次有界A查询及独立渠道查单；过期响应丢弃本地写回，新租约查原键；本阶段无需跨成员续租，退款续租仍按D10 | 2026-10-11按用户授权采用推荐；.2已实现并验收通过 |
| B05-D13 | 临时阻断以teamId归属、版本单调 | MQ可早于核对task创建；ownerId=teamId，task负责冻结提交；可信终局只清本team且不高于终局的版本，旧无归属review保留LEGACY | 2026-10-11按用户授权采用推荐；.2已实现并验收通过 |
| B05-D14 | 新超窗渠道事实可核对，历史不明review仍隔离 | 新事实在写review前由M2登记归属，仍停普通支付；稳定refundId先落库，原complete返回FAILED后才ELIGIBLE；未来渠道时间/真实冲突不放行 | 2026-10-11按用户授权采用推荐；.2已实现并验收通过 |

方案来源为本轮用户授权按推荐决定，并非逐项确认；D12细化D10，仅本阶段单成员短调用无需跨成员续租。新建block/refund行在已锁住订单/支付且通过task fencing后插入，不与既存行锁形成反向依赖；已有block/refund一律完整前缀锁定。证据关联按未关联Inbox/工作有界扫描，不能反复只扫最新工作而饿死旧证据。

### 11.2 已执行批次（进行中，后续追加最终证据）

- build-01日志：调度器引入未声明SLF4J依赖导致编译失败；改用JDK日志。build-02：87项中1项因领域ID抛错类型失败，统一不可核实证据IllegalArgumentException。早期provision使用旧产物失败且未执行V14，保留01/02报告和日志，不冒充已迁移。
- b052-20261010-03-sql：双库V14/41授权成功，未付关闭成员核对失败。定位JSON列规范化后不能直接按读取字符串校验原请求摘要；改为与原关闭路径相同的TreeMap规范化，保留原closeId/原hash。
- b052-20261011-04-sql：上述路径通过，回滚测试工具在事务内取模拟A证据触发隔离断言；将证据读取移到事务外，业务适配持续禁止事务内网络。
- b052-20261011-05-sql/report.json PASSED：87项JUnit构建、双库V14/41权限、真实MySQL/独立渠道/受控A、未付唯一RELEASE、支付原Outbox、缺成员禁止提交、原提交丢响应、新JVM且checkout关闭恢复、行锁实际跨租约/换token、原子回滚、自有阻断/旧review保护；1522条旧资金/HELD/guard/渠道/原工作保护记录变化0，样本新增保留。
- 新增超窗资金故障及稳定义务/原提交ACK资格用例，真实A三B成员自然到期验证运行中。最终结果在下节追加，不能将受控A证据冒充真实A。

失败批次与原始样本均保留，不修库凑通过；开发日期跨2026-10-10/11，报告名按实际创建时点。87项测试包括10项新核对行为用例，其余为既有回归。HTTP6操作仍design-only，退款执行.3、退款消息.4及收尾页面.5未开展。

### 11.3 用户暂停时的持久接续（2026-10-11）

用户明确要求“暂停任务，保存工作进度，等到明天我说恢复工作再接着完成该任务”。本阶段未完成，等待该恢复指令；不自动继续验收、开发或推进.3。自有验收进程已停止，未停止共享MySQL/Redis/RocketMQ；代码、迁移和所有资金/库存/中断样本保留，不回滚或清库。Git仍b-05/53ad32d222cdcb1b330cf07a53b2fd64e02ccccf，全部改动未提交/合并/推送。

已完成及证据：

- 最终源码构建日志target/reconciliation/b052-build-08.log：七模块package成功，87项JUnit零失败/错误/跳过；新增10项核对行为测试。最终verification包SHA256：C652273BF3D06A62EC4607DB5A8E29A465D8950B1FCEC8F5ECCAAF7AA0AB1B16。
- target/reconciliation/b052-20261011-07-sql/report.json PASSED：双B库V14/41表DML权限、真实MySQL/受控A/独立渠道、完整名单、缺本地成员阻止局部提交、原未付关闭一次RELEASE、真实锁等待跨租约和旧token替换、原子回滚、自有阻断/旧LEGACY保护、超窗义务先持久稳定refundId且无普通支付Outbox、原提交ACK后才OUTSIDE_WINDOW_RESOLVED、checkout关闭的新JVM重放原请求。1573条原工作/资金/HELD/guard/渠道保护记录变化0，新增记录保留。
- target/b03-readiness/b052-20261011-live-02/report.json及reconciliation.txt/reconciliation-recover.txt PASSED：真实A/TLS/签名MQ、全部3成员由B创建、自然2分钟到期、完整名单、两笔原未付关闭/各一次RELEASE、一笔原已付HELD、A提交成功但模拟丢响应后新JVM按原completionId/checkedAt/hash重放并持久一笔ELIGIBLE/funds NONE。环境恢复、自有端口释放、默认Java8未改。该批次包是build-06时期；其后仅修正证据关联SQL歧义/失败计数与告警，并新增成团竞争验收，不能将它冒充最终包全部真实联合验证。
- 06-sql首次执行新增证据关联扫描失败，原因INSERT SELECT的ON DUPLICATE UPDATE中work_id歧义；已明确目标表列名，07-sql发现/关联扫描成功。成功阶段清连续技术失败计数，5次失败记录alert并发出告警后继续恢复。初轮真实A live-01因新配置漏显式@Import失败，已将ReconciliationConfiguration加入ZjMarketApplication，live-02验证装配成功。所有失败批次保留，不改旧报告。

暂停中断：target/b03-readiness/b052-20261011-completed-01，在准备新批次时停止，尚无report.json/成团竞争通过结果；另写pause.json标识人工暂停。不能把它当业务失败或虚构通过。恢复时先查fixtures.json、准备日志及自有端口，不覆盖该目录；用新RunName再运行。中断可能已注册本批次用户/商品，保留即可，不清历史样本。

恢复后的必要事项（按顺序）：

1. 重新检查当前Git、实际源码/包指纹、V14/权限及自有进程；本目录是唯一实施工作树，不假设任何改动已提交。A、旧V1～V13和B04工作树不改；主B只插入本轮D12～D14决策，原差异保留。
2. 完成最终包真实A成团竞争：3笔原渠道付款均在窗口内，先送2笔，A自然RECONCILING后建立核对阻断，再用重新认领的原第三笔Outbox发送，A COMPLETED须清自有阻断、原3 CONFIRM/3 PENDING、零退款/零RELEASE；不能凭受控A设置COMPLETED替代。
3. 必要时用最终包重跑真实A部分付款/原提交丢响应新JVM恢复，以同包收口；现live-02的通过事实独立保留。
4. 执行受影响的既有run-b04-payment-closing.ps1、run-b04-settlement.ps1、run-b04-fulfillment.ps1专项回归，全新批次，顺序运行避免全局扫描互相影响。普通包无Flyway/verification、默认写关闭、旧迁移/A契约及原文/资金保护/主路线图插入外字节检查尚待最终归档。前端没改，本轮未跑浏览器，不把.0历史浏览器证据算本轮。
5. 复核实现（含COMPLETED竞争、保存完整名单与唯一提交、未知不换键、锁后DB时间、证据关联、公平恢复）；只有全部必要检查通过后才将.2标完成，更新本过程、路线图、联合设计当前状态及交接入口，并新建最终交付报告；.3退款执行仍待用户启动。

复现入口（均使用新批次名，PowerShell，JDK21）：

```powershell
./docs/tests/run-b05-reconciliation.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <新SQL批次> -SkipBuild
./docs/tests/run-b03-readiness.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -WithReconciliationCompletion -RunName <新成团竞争批次> -SkipBuild
./docs/tests/run-b03-readiness.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -WithReconciliation -RunName <新部分付款批次> -SkipBuild
```

跳过构建仅在确认同一当前包时使用；若改代码须重建并按变更复验，不覆盖旧批次。不要重跑临时安装/补修Python writer（非幂等）；实际工作树源码已包含其修改，scratch模板可能过时。当前没有待答方案问题，D12～D14已按用户授权推荐决定并记录双路线图。

### 11.4 恢复工作与最终验收（2026-10-11，已完成）

用户明确“恢复工作”，撤销11.3暂停要求并沿原B-05.2目标继续，不启动.3。Git b-05/53ad32d及未提交文件与暂停一致；逐Java源码SHA256变化0，verification包仍C652273BF3D06A62EC4607DB5A8E29A465D8950B1FCEC8F5ECCAAF7AA0AB1B16。恢复检查时A及B04工作树无差异；后续A外部配置变化见下文。Docker daemon恢复时未运行，启动既有Docker Desktop并检查原容器，不重建或清库。新验收只使用新批次，completed-01/pause.json及历史报告原样保留。

简洁实施计划：复核基线/环境→最终包真实A最后付款成团竞争及部分付款核对恢复→顺序运行关单/结算/履约专项回归→核对原SQL/A契约/权限/普通包边界和旧保护记录→新交付报告及四份接续文档收口。新增方案沿D12～D14；发现事实差异按用户授权推荐决定并持久记录。实际结果后续追加。


恢复后上述计划全部完成，最终交付报告target/reconciliation/b052-20261011-delivery-03/report.json PASSED。.2实现复杂度高，实际资金与库存安全由分层证据共同验证，不以单元测试代替联合验收。

| 最终证据 | 结果及边界 |
| --- | --- |
| target/reconciliation/b052-build-08.log | 七模块构建、87 JUnit（新增10项），失败/错误/跳过0；恢复后Java源码指纹变化0 |
| target/reconciliation/b052-20261011-07-sql/report.json | 真实MySQL/独立渠道/受控A/两个JVM，完整名单、缺本地成员拒绝局部提交、原未付关闭唯一RELEASE、原支付Outbox、冻结提交丢响应、超窗稳定refundId与原ACK资格、真实行锁等待跨租约/换token、回滚、阻断归属保护；双库V14/41表最小DML |
| target/b03-readiness/b052-20261011-completed-02/report.json | 真实A/TLS/签名MQ、3个B成员原付款均在窗口内；先2笔被接受，A自然RECONCILING后建立阻断，再重新认领第三笔原Outbox使A COMPLETED；清自有阻断，原3 CONFIRM/3 PENDING，零退款/零RELEASE |
| target/b03-readiness/b052-20261011-live-03/report.json | 同最终包真实A，3个B成员自然2分钟到期、一付两未付；原closeId及各一次RELEASE；原complete落A后注入丢响应，新JVM按原completionId/checkedAt/字节/hash恢复，A FAILED、任务RESOLVED，一笔ELIGIBLE/funds NONE，付费HELD保留 |
| target/payment-closing/b052-20261011-closing-regression/verify.txt、recover.txt | 原根竞争、未知保持HELD/guard、冻结关闭、迟到事实/隔离/回滚、实际到期、A离线及新JVM恢复 |
| target/settlement/b052-20261011-settlement-regression/verify.txt、recover.txt | M2/Outbox原子性/幂等；通知ACK及retry实际锁等待跨租约、换token；签名MQ、冲突/缺订单/D6、拒绝及超窗资金保留、A离线新JVM |
| target/fulfillment/b052-20261011-fulfillment-regression/verify.txt、recover.txt | 全量查询、原子回滚/插入失败、认领竞争/租约/归属、唯一CONFIRM/PENDING、新guard及跨JVM安全 |
| target/reconciliation/b052-ordinary-start/report.json | 普通zj-market-app-exec.jar默认配置实际启动/停止；无Flyway及verification，无默认核对调度/资金写开启 |
| target/reconciliation/b052-final-protected.txt | 全部回归后1573条原资金/工作/HELD/guard/渠道保护记录丢失或变化0；新样本保留 |

各真实A批次环境恢复、自有端口释放、默认Java8未改变。仅本任务自有进程停止，共享容器保留。SQL全未付路径使用受控A，不声称已完成.6全部真实A矩阵；本轮没有前端修改或浏览器验收。实际A原包SHA256 223A02521120F6D83CB58220E7CFF08839A5B6BCBAC9BC5C00BCA42F8E6C8392；契约83B02A7EBF5E80B5EF4D1B03936E6B1CA33EED32F6D9C68B451E855C6192D7DD；普通exec包272ED0CE489670269835A3847B8A0309ED58ACDC525B433221FA9A20C65C2838。最终verification指纹与11.3相同，受影响专项及两个真实A批次均验证此包。

归档期间A工作树出现外部修改：application-dev.yml、application-prod.yml、application-test.yml三份源配置，未由本任务写入，已原样保留。A HEAD仍8c0a3fa，实际测试原包及契约未变；仅记录路径/指纹，不复制配置值。target/reconciliation/b052-external-a-state.json保存范围快照。首轮delivery报告因原“必须A clean”检查拒绝归档，保留FAILED；collector改为显式快照严格限定这三份配置并校验字节、HEAD、实际A包/契约，delivery-02及最终delivery-03通过。不忽略其他A变化；源码配置重建后的A需要另行验收，当前结论只覆盖实际测试包。B04工作树无差异；主目录仅更新原授权D12～D14块及边界快照，剥离插入后原SHA256不变。

归档复现（需保留本地原始批次、保护快照及外部范围快照；全新RunName，不覆盖历史）：

```powershell
python -X utf8 docs/tests/collect-b05-reconciliation.py --run-name <全新交付批次> --sql-batch b052-20261011-07-sql --completed-batch b052-20261011-completed-02 --partial-batch b052-20261011-live-03 --regression-prefix b052-20261011 --protected-after target/reconciliation/b052-final-protected.txt --external-a-snapshot target/reconciliation/b052-external-a-state.json
```

最终实现边界：D12“每租约一个成员”针对名单收集；终局处理逐成员独立事务、每次租约fencing，不持全团队订单锁。.2实现扫描2秒、A调用10秒、租约30秒、有界退避2/4/8/16/30秒及≤250ms jitter、连续5次技术失败告警后继续恢复；这些是固定默认值，退款参数化及20秒续租仍归.3，未冒充已实现。block以teamId归属（D13），新超窗事实先登记自有阻断再兼容review投影（D14），历史不明review仍LEGACY。旧迁移不改，V14已应用，.3扩展funds NONE约束须追加迁移，不能重写V14。

B-05.2已完成，无待答方案；.3退款执行、.4退款MQ、.5运营/收尾页面、.6联合完整矩阵未开展，六项B05 HTTP仍design-only。Git仍b-05/53ad32d，全部阶段变更未提交/合并/推送；后续由用户启动.3，沿本过程及路线图继续维护。

## 12. B-05.3 独立模拟退款（2026-10-11，已完成）

事实基线：b-05/53ad32d、.0～.2未提交成果、双B库V14/41表；参考B04交接和当前联合设计。初次受限Git status无法访问工作树元数据，提升只读核对后确认实际工作树和全部原差异；不据失败输出猜测仓库损坏。源码/迁移/文档指纹及Git状态保存target/refund/b053-baseline/before.json。

实施计划：V15五表及46表精确DML→独立渠道执行/查单/通知→商城资格复核、原键恢复/续租/退避及冻结版本事实→真实SQL/跨JVM/锁等待/并发和原回归→最终证据及文档收口。退款成功保留原收款与HELD/guard；退款MQ与库存释放归.4/.5。

| 编号 | 推荐方案 | 影响与约束 | 来源／状态 |
| --- | --- | --- | --- |
| B05-D15 | .3持久冻结每次尝试的PENDING/终局版本事实，.4再原子补建交易Outbox | 不提前放宽V11支付消息约束；冻结版本/时间/业务事实/hash支持.4幂等追补，不遗漏退款成功；.3不宣称A已同步 | 2026-10-11用户授权按推荐确定；.3已实现并验收通过 |
| B05-D16 | 退款任务和通知分别续租，调用前查原尝试，未知不换键 | 可配置并验证timeout<lease及renew<lease；锁后DB时间/token/intent校验；失败新attempt、refundId不变，业务失败也有界退避 | 2026-10-11用户授权按推荐确定；.3已实现并验收通过 |
| B05-D17 | 联合验收端口可参数化，只管理本批自有A | 默认50051/18091保持；被外部A占用时显式选50052/18092，B定向TLS连接、清理只验证自有端口，不停用户进程或改A源配置 | 2026-10-11用户授权按推荐确定；隔离端口全链路验收通过 |

当前主要风险为未知重试二次退款、资格过期/履约冲突、渠道与商城锁反向、旧租约响应污染及事实到后续Outbox的可靠衔接。实现按独立事务和完整绑定解决，验收使用新增隔离样本，不清历史失败/UNKNOWN/HELD/guard。

### 12.1 实施与中间验收

实现domain/refund、独立SimulatedRefundChannel、RefundRepository、RefundConfiguration/RecoveryJob及V15五表；双库V15/46精确授权通过。D15将PENDING/FAILED/SUCCEEDED业务版本与时间/字节/hash冻结在每次attempt，UNKNOWN不新增对外版本，.4再原子幂等补Outbox；.3不放宽原PAYMENT_SUCCEEDED约束、不发送退款MQ。D16采用配置扫描/超时/租约/续租/退避且校验大小关系，续租失败拒绝本地写回，锁后DB时间验证state/token/intent。M1原请求在调用前持久possible_sent；先查原尝试，执行前再次完整订单锁前缀校验资格。C1按原sim payment→sim refund→attempt→notice独立事务裁决全额退款；M2保存完整可信渠道事实与单调版本同事务，通知仅唤醒/查原渠道再与已持久同一typed Fact核对后ACK。已有成功不可降级，同版本异事实隔离；资格在C1后变矛盾仍保留实际退款成功，同时隔离、不释放。

12项新退款行为测试，总99项JUnit通过；build-01因ContractCodec摘要方法checked exception漏适配编译失败，build-02起通过；全部日志保留。SQL01双库迁移/授权成功，但C1使用了错误的普通JSON序列化顺序校验原支付successHash，合法事实被安全拒绝；改为沿用原ContractCodec。SQL02通过退款主流程、并发及真实租约竞争后，通知比较因JSON IntNode/LongNode类型差异误判，改为反序列化完整typed Fact比较。未修改原支付字节/时间/hash或清失败样本。

SQL03报告target/refund/b053-20261011-03-sql/report.json PASSED，1810条旧保护记录变化0。真实MySQL/独立渠道/受控A生成资格、UNKNOWN原attempt且5次告警、5次明确失败后第6尝试成功/12版本、8并发同请求一笔成功、C1通知插入故障全回滚、M2版本/资金/任务回滚、实际Future超时及丢响应/丢通知、成功续租跨原租期、执行前资格变化拒绝调用、C1后冲突保留退款成功、同版本异事实隔离、市场finish/defer/renew及通知ACK/retry/renew共12组真实行锁等待跨租约/换token、两独立JVM分别恢复M1前调用及C1后M2前中断。HELD/guard/原支付保持，库存释放归.5。随后仅强化传入Lease与已持久原Request精确相等、生产admit复用和真实A验收入口，最终SQL04及真实A/回归待追加；不能把SQL03的较早包冒充最终同包结论。

真实A live-01/02在创建样本之前因50051占用失败，报告保留。受限Get-NetTCPConnection未显示外部listener，提升只读检查确认JDK8进程18952自10:48:27运行；不停止它。当前A原jar及契约指纹未变、三份既有外部源配置保留。按D17给verification脚本增加AProviderRpcPort/AProviderHttpPort及B定向TLS/自有端口清理/报告，使用50052/18092新批次；不改A源码、业务或默认端口。

真实A live-03在嵌套run-b01-environment基线中仍使用默认50051，未启动本批业务样本即失败，自有50052/18092已确认释放。已把同一D17端口参数贯穿基线RPC及provider启动，保留失败报告；live-04重新开始。普通执行包默认启动startup-01已通过，未启数据库/核对/退款恢复，进程和Java环境恢复。

真实A live-04隔离A在50052成功启动，前置EnvironmentProbe仍把URL写死50051导致configuration拒绝；补为严格匹配显式B_PROBE_RPC_PORT（默认50051、限制合法端口且仅127.0.0.1/TLS），脚本传入并恢复该环境变量。此变更仅verification，业务源码不变；因验收包重建，SQL05及真实A live-05使用同一最终新包，SQL04旧包报告独立保留。

### 12.2 最终同包验收与交付

本阶段已完成，无待答方案。最终构建target/refund/b053-build-07.log：七模块成功、99项JUnit（新增退款12项），失败/错误/跳过0。SQL05、真实A live-05、actual-01及三个专项回归均使用同一最终verification包；首轮delivery-01和文档收口后的delivery-02归档检查通过，报告不覆盖历史批次。

| 最终证据 | 已验证行为与实际边界 |
| --- | --- |
| target/refund/b053-20261011-05-sql/report.json | 双库V15/46精确DML、真实MySQL/独立渠道/受控A资格/两个JVM；全额守恒、8并发同键一笔成功、UNKNOWN原attempt且持续恢复、5次FAILED后第6尝试成功并冻结12版本；1960条该批前保护记录变化0 |
| SQL05 verify.txt/recover.txt | C1通知插入故障全回滚、M2资金/版本/任务回滚；实际Future超时、渠道提交后丢响应/丢通知；调用跨初始租约且成功续租；执行前资格变化拒绝、调用后冲突保留实际资金成功并隔离；同版本异事实隔离；市场finish/defer/renew、渠道通知ACK/retry/renew分别实际锁等待跨租约和换token，共12组；M1后调用前/C1后M2前由新JVM原attempt/hash恢复，checkout/新退款接管关闭 |
| target/b03-readiness/b053-20261011-live-05/report.json | 真实A/TLS/签名MQ、全3成员由B新建、自然2分钟到期、一付两未付、原closeId/各一次未付RELEASE；A已落核对提交但丢响应后新JVM按原completionId/checkedAt/hash恢复，可信FAILED/ELIGIBLE；50052/18092自有端口释放、环境/默认Java恢复 |
| target/refund/b053-20261011-actual-01/report.json / actual.txt | 上行真实A新样本的唯一付费成员；确认自有A已停止，在无RPC/MQ的独立DB启动新JVM中，用真实已保存资格全额退款一次，重复恢复不加第二尝试；2冻结版本，原支付successHash/核对hash/HELD/guard保持，未新增付费RELEASE，两个原未付RELEASE仍唯一 |
| target/payment-closing/b053-20261011-closing-regression/verify.txt、recover.txt | 原关闭根裁决/冻结请求/UNKNOWN/原资金/HELD/guard/真实锁等待、A离线新JVM等原专项通过 |
| target/settlement/b053-20261011-settlement-regression/verify.txt、recover.txt | 原支付M2/Outbox/签名结果/D6/通知ACK及retry实际跨租约、换token、跨JVM恢复通过 |
| target/fulfillment/b053-20261011-fulfillment-regression/verify.txt、recover.txt | 原成团全量查询/事务回滚/租约/多worker/归属及新guard保护、唯一CONFIRM/PENDING、新JVM恢复通过 |
| target/refund/b053-20261011-startup-02/report.json | 最终普通exec默认实际启动，无默认数据库/退款/核对外部执行，普通包无Flyway/verification，停止仅自有进程，默认Java8不变 |

真实A四个早期失败批次已保留：live-01/02为外部A占用默认50051；live-03为嵌套环境基线未透传隔离端口；live-04为旧EnvironmentProbe固定URL断言。均在业务新团队验收之前失败，不算退款业务失败或通过；D17修复后live-05全链路通过。未停止外部18952进程，A原jar/契约与三份外部配置指纹保持；不改A业务源码。共享MySQL/Redis/MQ容器保留。前端本阶段无变更、未跑浏览器；.6全矩阵仍待做，不将本轮受控故障冒充真实A退款消息/库存闭环。

退款版本、阶段边界与接续：b_refund.version是行并发版本，fact_version是对外业务版本。每attempt冻结pending_version/pending_fact/pending_hash及终局result_version/result_fact/result_hash，未知不另造版本，成功原事实永不回退。task DONE仅表示本阶段资金已确认，不完成原REFUND_OBLIGATION工作或清HELD/guard；.4必须从全部冻结版本追补Outbox（包括资金任务DONE或隔离的真实成功），用原事实occurredAt/业务字段并保证同一版本唯一事件，不能只扫活跃退款任务。尚无退款A ACK/库存释放/HTTP上线声明。当前执行资格仅复用.2已落地TEAM_FAILED_ACCEPTED、OUTSIDE_WINDOW_RESOLVED；取消迟到收款资格生成与证明适配仍待后续，A_REJECTED或不明旧review不会被盲退。

本机复现（全新批次；凭据只读被忽略DPAPI，不能覆盖旧报告）：

```powershell
./docs/tests/run-b05-refund.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <新SQL批次> -SkipBuild
./docs/tests/run-b03-readiness.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -WithReconciliation -AProviderRpcPort 50052 -AProviderHttpPort 18092 -RunName <b053-新真实A批次> -SkipBuild
./docs/tests/run-b05-refund.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -ActualBatch <上行真实A批次> -RunName <新独立退款批次> -SkipBuild
./docs/tests/run-b05-refund-startup.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <新普通启动批次>
python -X utf8 docs/tests/collect-b05-refund.py --run-name <新交付批次> --sql-batch b053-20261011-05-sql --actual-batch b053-20261011-live-05 --refund-actual-batch b053-20261011-actual-01 --regression-prefix b053-20261011 --startup-batch b053-20261011-startup-02 --protected-after target/refund/b053-final-protected.txt
```

SkipBuild仅在核对同一当前包指纹后使用。collect只归档检查，不重跑业务，依赖原始证据/阶段前指纹/主目录边界快照/既有A外部配置快照；不将历史暂停或失败批次覆写为通过。主目录仅更新本阶段D15～D17块，其他字节SHA保持。V1～V14不变，V15已应用，后续必须新增迁移。Git仍b-05/53ad32d、全部阶段变更未提交/合并/推送；.4～.6未开始，后续依本过程及路线图继续。

最终verification SHA256：A0497BE7918C01542744D7BBCC173CF85CD36E3D55D36B6B4967E1D1800DFD93；普通exec SHA256：74275F8D8EF12A3A8336FD6F90716B0FCCE87EFB508B0174AABC54264BE33117。最终交付核实全部阶段前保护记录1700条，丢失或变化0；新失败及故障样本保留。

## 13. B-05.4 可信退款事实与A同步（2026-10-11，已完成）

基线：b-05/53ad32d，.0～.3全部未提交；V15/46表；以12.2同包证据及b04-b05-handoff.md为接续事实。先核对原支付Outbox只支持version1、退款版本已冻结、A契约8.4及当前V2EventEngine。实施顺序：V16增量能力→新版本原子Outbox/旧事实追补→严格回执与完整交易查询→真实SQL/跨JVM/实际A签名MQ/RPC及原链路回归→文档收口。

新增推荐选择D18/D19已记录双路线图。正常资金任务DONE不表示同步完成；A离线仍按原渠道退款，接受高水位独立，UNKNOWN不产生新对外版本。库存释放/运营接口/页面归.5。保留全部旧资金/HELD/guard/事件字节，不改已应用V1～V15/A源码与外部进程。当前尚未执行V16，不将设计声明为验收完成。

### 13.1 实施与当前验证进度

V16增量替换原支付类型CHECK时按information_schema精确定位，不依赖自动约束编号；保留uk_trade_fact和支付version1/null refund约束，增加退款复合FK、正版本、同步高水位及typed RPC authority原文/hash。双B库已执行，runtime仍46表精确DML，旧V1～V15不改。

RefundOutbox按refundId+businessVersion生成固定64位eventId，冻结pending/result版本转换原信封，复制原occurredAt/paidAt/金额，追加原userId；不发送内部channelFact。RefundRepository的M1/M2与事件同事务；UNKNOWN不新增版本。恢复从缺失版本查询追补，不限活动任务，DONE及资金成功后隔离者亦覆盖。逐单坏证据隔离，不使一条毒事实永久占满补建扫描或停止原支付。已有Outbox按eventId排序先锁；同单新事件在完整订单前缀串行期间首次插入，没有已存在行的反向回锁。

复用原交易topic/独立交易结果组、签名与严格结构；商品reader不接管退款。退款结果独立应用，不修改payment.a_acceptance、退款资金、库存或guard。高版本必须本地已冻结同状态，MQ高版本缺完整查询先持久等待；认证Event.query和typed Trade.query将完整快照独立持久authority/hash，不能把RPC结果伪称为收到MQ。严格核对原订单/用户/source/channel/团队、原payment/amount/currency/paidAt、退款及recordVersion；异常超窗记录的Trade.query不返回独立异常payment，按冻结异常资格/原收款与CANCELLED返回核验，不能编造查询字段。未知高版本/同版本异状态/异绑定/拒绝留档隔离；旧版本及重复不降低接受高水位。同步摘要变化递增行version，fact_version只由退款业务变化递增。

D20错误退避沿退款配置，5次告警后继续恢复；正常PUBLISHED30秒补查。退款投递写回同完整前缀、锁后DB时间校验原token/lease；任何Broker ACK不替代A接受。关闭新退款接管后，原trade events扫描仍承担已冻结事件；人工关闭整个恢复能力时按开关停止，不能宣称已同步。

验证历史保留：build02仅verification报告字符串换行编译失败，build03修正；SQL01严格拒绝受控样本FAILED但复用FORMING同teamVersion，修正测试快照并补上旧待查消息不降ACCEPTED摘要；SQL02通过（旧保护2198变化0）。真实A live01完整核对资格通过，但离线测试误开支付能力且关闭订单依赖，装配失败、清理通过；修正专用模式开关后最终候选build05/103项JUnit通过。最终SQL03、live02、原专项及普通启动验收进行中，不覆盖这些历史失败报告。

### 13.2 同包验收结果与B-05.5接续

build05全部103项JUnit通过。最终verification SHA256=77D510F704548852071114794F060C3B15063F735267B7494F9C400C9899ED5D；普通exec SHA256=524D9C8F7B74AA77CA50F674E23D8CD4F7F6EE226E767AB50FCBEE3EC5A5C3C3。

| 证据（均为同最终包） | 实际验证范围 |
| --- | --- |
| target/refund/b054-20261011-sql-03/report.json、sync.txt、verify.txt/recover.txt | 双库V16/46表权限；完整受控资格及独立渠道；M1/M2与事件原子性、终端Outbox同回滚、所有冻结版本（含DONE/REVIEW）追补及原字节不变；Broker ACK不认A接受；真实Outbox锁等待跨租约/换token；高版本缺查询等待、本地已知高版本+完整查询接受、未知高版本/同版本异状态/原payment金额/异订单/确定拒绝隔离；旧回执/重复不降高水位；两JVM原attempt恢复；资金/HELD/guard保持。该批受保护旧记录2888条变化0（包含原Outbox/退款版本字节hash） |
| target/b03-readiness/b054-20261011-live-02/report.json及reconciliation/refund各阶段txt | 实际A/TLS/签名MQ，新三B成员团队自然两分钟到期，完整核对提交丢响应后原completion跨JVM重放→FAILED/可信资格。只停自有50052/18092 A，DB-only新B进程独立退款一次+两版Outbox同事务保存；新A启动后先成功v2再待退v1，真实签名MQ旧结果带当前v2→持久等待→认证Event.query+完整Trade.query核验→ACCEPTED；typed Trade.query补偿与重复原事件；再新B进程恢复。paidAt/原支付/hash/两事件hash/付费HELD/guard/一次渠道退款不变，自有进程/端口及调用环境清理通过 |
| target/payment-closing/b054-20261011-closing-regression/verify.txt、recover.txt | 原完整根关闭/竞争/事务回滚/丢响应/真实到期/新JVM全部通过 |
| target/settlement/b054-20261011-settlement-regression/verify.txt、recover.txt | 原M2/支付Outbox原子性、签名结果、实际通知锁等待ACK/重试/换token、原paidAt晚通知/A离线与新JVM回归通过 |
| target/fulfillment/b054-20261011-fulfillment-regression/verify.txt、recover.txt | 原CONFIRM/PENDING原子性、租约/游标/新guard隔离及新JVM恢复通过；只按PAYMENT_SUCCEEDED读取/锁定支付接受 |
| target/refund/b054-20261011-startup-01/report.json | 普通应用默认关闭DB/RPC/MQ/资金能力，JDK21实际启动并只停本批进程；默认Java8不变，普通包无verification/Flyway |
| target/refund/b054-20261011-delivery-02/report.json、b054-final-protected.txt | 只读最终归档：同包、旧迁移指纹、双库精确权限、A包/契约/原三配置文件不变、B04干净、主目录仅新增D18～D20块、全部阶段前2123条资金/工作/退款/HELD/guard/渠道保护记录变化0 |

最终归档delivery01业务保护与全部业务报告均通过，因沿用旧工具要求A整个Git状态相同而失败：外部并行新增TagService.java修改及docs/project-a-v1-v2-comparison.md，原三配置/hash、A HEAD/包/契约均保持。没有覆盖、清理或重新构建A；仅修正只读检查为保护原受保护文件和实际使用产物，记录target/refund/b054-external-a-state.json，再以delivery02收口。不能把该外部变化写成B业务故障。此前SQL01/真实A live01及build02失败继续保留。

复现（新RunName，SkipBuild须先核对当前包指纹）：

```powershell
./docs/tests/run-b05-refund-sync.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <b054-新SQL批次> -SkipBuild
./docs/tests/run-b03-readiness.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -WithRefundSync -AProviderRpcPort 50052 -AProviderHttpPort 18092 -RunName <b054-新真实A批次> -SkipBuild
python -X utf8 docs/tests/collect-b05-refund-sync.py --run-name <新交付批次> --sql-batch b054-20261011-sql-03 --actual-batch b054-20261011-live-02 --regression-prefix b054-20261011 --startup-batch b054-20261011-startup-01 --protected-after target/refund/b054-final-protected.txt
```

.4完成，.5接续：A接受与资金/收尾保持独立，原REFUND_OBLIGATION工作仍未宣称库存收尾完成。只凭可信全额退款/不履约证明原子RELEASE并仅清原guard；不得因ACCEPTED、旧未付关闭或重复回调释放，不改sold/CONFIRMED/PENDING。V17/收尾审计/六项HTTP及页面归.5，完整实际异常/故障矩阵归.6。本阶段不添加CANCELLED_LATE_PAYMENT资格生产：原渠道关闭后禁止再收款，未具合法声明的窗口内取消后异常收款继续保守隔离，不能谎称超窗或从未付款；后续若扩展须独立证明/验收。Git仍b-05/53ad32d，所有阶段改动未提交/合并/推送。

## 14. B-05.5 库存收尾及运营页面（2026-10-11，已完成）

事实基线为 b-05/53ad32d，B-05.0～.4未提交改动全部保留，V16/46表。先核对持久化文档、源码和Git，按用户授权选择D21/D22，已写双路线图。实施计划：V17及可信原子收尾；六HTTP/运营审计与仅查询CHECK；买家退款摘要、运营退款/核对页面；专项数据库/HTTP/浏览器/原链路回归。B-05.6不提前开展。A外部改动、运行服务和历史样本保留。当前尚无B-05.5验收结论。

### 14.1 首轮验证与方案补充

构建01/02及前端构建通过；SQL01已执行双库V17/48表精确权限，业务验收在原义务缺失处安全拒绝，报告保留。定位直接完整核对创建退款根不必经过MQ建原work，D24授权推荐补建原业务键义务，已有证据不改。另补CHECK原任务到期时间恢复，防止查单提前触发失败重试；V17已落库，新增V18而不改其校验和。D21～D24已写双路线图，专项复验待完成。

### 14.2 当前验证进度

SQL02/03及两JVM已通过，SQL03同包SHA963EB8AAF9F5EAEFE93705084516D6445EE46E99E475DBEDF55750B4B0A1DCAD，3433条旧保护记录变化0。原支付及库存原子回滚/唯一RELEASE/后来guard/实际跨租约行锁/HTTP归属与撤销权限/幂等均通过。浏览器01缺测试依赖、02定位器匹配两条正确库存提示，均保留失败报告；已补依赖并缩小选择器。新真实A批次将验证停机释放、两个新B进程及恢复后同步，不扩大.6完整矩阵。最终候选包仍需复验。

浏览器03最终候选包48318D843C8069DB74126265822D3A42FD7C2309F5CD6CB031C492E17E3709A4通过：真实B HTTP、买家全额退款/独立同步及库存、运营退款/核对、桌面及390px无溢出、刷新业务写0、丢响应同操作body重放。SQL04同包通过，3577条旧保护记录变化0。补充审查发现CHECK事实冲突后应清除已结束的查询标记，否则下一次运营查单不能重新领取；已修正并新增隔离状态再次CHECK、原计划恢复和intent围栏实测，需新候选包复验。

### 14.3 最终同包验收与交付

最终build08全部106项JUnit通过；前端生产构建通过（target/refund/b055-frontend-build.log）。verification SHA256=58191DB8A1D2AA1218C7E2C141308D6CD55E4ABD010A573480D3562E3D375EAF；普通exec SHA256=49FC0227450F7EBC7680B86BCA340B2D6DBED74E6C0C269605FD85DDB6232F8A。V17/V18均已应用双B库，runtime48张业务表精确DML，不能改已应用V1～V18。全部后续测试复用这两个包，不重建A或覆盖旧报告。

| 同包证据 | 实测范围 |
| --- | --- |
| target/refund/b055-20261011-sql-05/report.json、release.txt、sync.txt、verify.txt/recover.txt | 真实MySQL/独立模拟渠道/完整受控资格/两JVM；全额资金及原资格核验、原义务缺失补建但已有字节不动；释放事务整体回滚、6worker唯一流水、重复证明核验及后来guard安全、证明/intent/原工作绑定围栏；实际行锁等待跨租约及token更换。CHECK失败/UNKNOWN只查原尝试、恢复原到期时间、冲突隔离后仍可再CHECK；RETRY仅唤醒，不内联退款；本人/外人/撤销运营角色、严格参数/一致快照/同键重放与异请求409。3734条旧保护记录变化0 |
| target/refund/b055-20261011-browser-04/report.json、browser.json | 实际B HTTP、SQL05保存的资金/证明（A资格受控）；买家退款/资金同步库存独立摘要、运营退款与核对；桌面和390px窄屏无溢出/pageErrors0；读刷新业务写0；操作已在服务器提交后丢响应，刷新后同body/operationId得到原200回执。不是用假页面接口替代B验收 |
| target/b03-readiness/b055-20261011-live-02/report.json及refund各模式txt | 实际A新三B成员团队自然到期→完整核对原提交丢响应跨JVM恢复→可信资格；只停自有50052/18092 A，新DB-only B全额退款一次，在无A ACK时原子释放；另一新B按原证明重放无第二RELEASE；新A恢复签名MQ/认证Event.query/typed Trade.query，同步ACCEPTED后再新B恢复，原支付/事件字节/sold/唯一流水保持；自有端口、调用环境和默认Java清理通过 |
| target/refund/b055-20261011-final/report.json及各log | 原关单/结算/履约专项分别verify/recover通过；证明感知的B04全库只读审计通过；普通应用默认真实启动、停止仅自有进程、默认Java8保持；回归前旧资金/退款/工作/HELD/guard/渠道及原字节记录无改变 |
| target/refund/b055-20261011-delivery-03/report.json | 最终只读归档：同包、V1～V18冻结校验和、双库48表权限、实际HTTP响应符合六项契约、106项JUnit、普通包无Flyway/verification且A契约保持Java8、A原产物/契约/外部差异、B04干净和主目录仅D21～D25插入块；全部阶段前保护记录无改变 |

首轮SQL01安全拒绝缺原义务、浏览器01缺依赖/02选择器歧义及中间候选的通过证据均原样保留；最终只认上表同包。最终补修CHECK冲突后清理已结束查询标记、恢复原调度和原工作/intent围栏均由SQL05覆盖。资金成功不回退，原Payment及PAID渠道根保持，收尾不修改sold或CONFIRMED/PENDING，原Settlement再唤醒不把CLOSED退回WAITING_REFUND。

### 14.4 实现边界与B-05.6接续

D21～D25已保存活动工作树及主目录路线图，主目录其他原字节保持。收尾复用原REFUND_OBLIGATION完整锁序，持锁后DB时间校验租约/token/intent与冻结资格/成功hash；缺原义务仅在资格通过后按paymentId:orderId补建。已有work证据不覆盖。库存、唯一账本/证明、订单FULL_REFUND_CONFIRMED关闭、仅原guard和work DONE同事务；写失败向外抛出使整体回滚。A暂不可用不是前置阻断，明确同步矛盾则隔离尚未发生的释放。

已释放重放重新核验完整证明、原根/支付/退款版本/hash及唯一库存流水。ALREADY_RELEASED分支严格要求原未付关闭类型/绑定/hash/流水，不重写原关闭或后来guard；本轮没有合法取消后收款资格生产，不能伪造正向迟到资金样本宣称此路径全链验收。当前TEAM_FAILED_ACCEPTED/OUTSIDE_WINDOW_RESOLVED资格可执行；未具可信资格的取消后异常资金继续隔离，完整正向异常生产及故障矩阵留给.6，不以“已退款”按钮代替证明。

六HTTP按b05-http-api.json实现，增量列表0起始分页、size1～100，原订单分页保持1起始；未取得的核对标识/版本为null。服务端allowedActions决定运营动作，GET一致快照零推进；CHECK仅原渠道查询/原同步查单，RETRY仅明确失败且资格仍有效/无活动租约时唤醒原任务。操作者+operationId冻结请求/响应，授权先于重放，相同键异请求409。运营页面持久原请求，响应不确定先恢复，身份变化阻断旧身份动作；不暴露原始证据/签名/租约或提供强制退款。

可复现入口（必须全新批次，SkipBuild前核对包指纹）：

```powershell
./docs/tests/run-b05-refund-release.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <b055-新SQL批次> -SkipBuild
./docs/tests/run-b05-refund-browser.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <b055-新浏览器批次> -SqlBatch <上行SQL批次>
./docs/tests/run-b03-readiness.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -WithRefundRelease -AProviderRpcPort 50052 -AProviderHttpPort 18092 -RunName <b055-新真实A批次> -SkipBuild
./docs/tests/run-b05-refund-release-regressions.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -Prefix <b055-新回归前缀>
python -X utf8 docs/tests/collect-b05-refund-release.py --run-name <新归档批次> --sql-batch b055-20261011-sql-05 --actual-batch b055-20261011-live-02 --regression-prefix b055-20261011 --startup-batch b055-20261011-startup --browser-batch b055-20261011-browser-04 --audit-batch b055-20261011-handoff --protected-after target/refund/b055-20261011-final/after-protected.txt
```

浏览器工具测试临时令牌仅存忽略目录，验收结束删除精确browser-private.json；复跑须新SQL批次生成本人凭据，不修改旧证据报告。SQL/关单等写库套件串行运行，避免旧全局调度误接他批新任务。共享中间件/外部A50051不停止，A源码/配置的并行修改不覆盖。工作树D:/Java/zj-market-b-05、b-05/53ad32d，所有B05阶段改动未提交/合并/推送；.5完成，.6未自动开展。

最终归档delivery01仅Git空白检查失败（B04HandoffCommands一处行尾空格），全部业务/外部边界/3145条阶段前保护记录检查已通过；删除该空格后delivery02通过，未改变Java标记/业务语义或已验收包。文档收口后再以delivery03只读复核；历史报告不覆盖。上文14节起始及14.1/14.2保留各时点的未完成状态，以14.3～14.4为当前结论。

## 15. B-05.6 联合故障验收与B-06交接（2026-10-11，支持范围验收已完成）

事实基线b-05/53ad32d，.0～.5所有未提交成果保留；双库V18/48表，.5交付delivery03通过。先读docs持久化入口/全部文档索引及B04交接，核对Git、原包与A实际源码。基线指纹target/b05-joint/b056-baseline/before.json。新增D26～D28按授权推荐，已保存双路线图，主目录仅新增本次选择行。

实施计划：补真实A无人付款完整到期/跨JVM和逐单库存资金报告，补窗口内渠道已付而受控A取消的保守隔离验收；同一最终包新批次串行运行核对、退款/同步/收尾/HTTP/浏览器、实际A部分付款停机闭环、最后付款成团竞争及原三专项回归；汇总脱敏覆盖矩阵与B-06配置/迁移/恢复/已知限制交接。故障仅verification，普通渠道/HTTP不添加故障能力。ALREADY_RELEASED合法正向生产未开放，不伪造验证；.6不自动部署或提交。

### 15.1 新增验收工具及首批进度

本阶段不改普通业务/渠道规则和已应用迁移。verification新增B05Conservation，按本批明确订单核验每笔RESERVE/终局RELEASE或CONFIRM、渠道退款累计不超过原收款、商城成功退款对应独立渠道成功，以及相关商品账户等于全部已提交库存流水增量；输出脱敏逐单金额/流水数，不打印凭据。ActualReconciliationCommands增加NONE无付款参数/新JVM恢复，保留原PARTIAL及全付款最后事件竞争；readiness脚本消除原阶段选择表达式中的重复开关赋值。受控A CANCELLED/窗口内渠道成功验收不得伪造CLOSED_UNPAID/PAID_OUTSIDE_WINDOW，无资格退款/RELEASE、原HELD/guard保持。

build01编译与106项JUnit通过，但审查发现新增守恒SQL误将payment_id当作b_sim_refund_attempt列；执行新业务测试前已改为经b_sim_refund关联，build02/106项JUnit通过。此问题属于新增验收代码，普通资金/库存源码未变。新串行总入口run-b05-joint.ps1，批次b056-20261011-01，旧隔离入口保留b055前缀保护，因此子批名b055-b056-20261011-01-*。核对SQL（2715条旧核心记录）/退款SQL（4014条旧完整保护记录）及浏览器均通过，变化0；真实A及原回归待完成，不提前标整个阶段通过。

新增collect-b05-joint.py将严格检查同一verification/exec包、三种实际A样本逐单结果、实际HTTP契约、原回归、只读审计/普通启动/权限/迁移、外部A与主目录插入边界；通过才可输出docs/tests/b05-joint-acceptance.json持久脱敏摘要。target原报告不覆盖、不随Git；B-06交接草稿保存当前支持范围及尚未启用的异常资格。前端本阶段无源码修改，生产构建通过，日志target/b05-joint/b056-frontend-build.log。

### 15.2 同包联合验收结果

新总批target/b05-joint/b056-20261011-01/report.json七阶段PASSED；最终build02/106项JUnit零失败/错误/跳过，前端生产构建通过。verification SHA256=B8245AE51B3085CCFE9A0112467287211D777B276DEC5C9E4EAE4EAE979EF28B；普通exec SHA256=B17DED82736AD7435814A247360BAB7C86C525979FCCF4A6EAB08688DCA5CFEC。本阶段只改verification及验收/持久文档，普通业务、A源码、前端业务源码及V1～V18不改。重建包的实际指纹以本段为准，不把.5产物冒称本批。

| 本批证据（子批共同前缀b055-b056-20261011-01） | 已验证结果及来源 |
| --- | --- |
| target/reconciliation/<前缀>-reconciliation/report.json、verify/recover.txt、cancelled-in-window-isolation-conservation.json | 真实MySQL/受控A：完整名单/缺成员禁止局部提交，原关闭/唯一RELEASE，窗口内晚观察原收款、超窗原声明/原提交ACK资格，提交丢响应新JVM恢复，真实行锁跨租约/token替换/事务回滚/临时阻断。新增窗口内渠道PAID而A CANCELLED隔离：资金SUCCEEDED、HELD/guard保留，无伪造未付/超窗声明或盲退款。2715条旧核心保护记录变化0 |
| target/refund/<前缀>-sql/report.json、verify/recover.txt、sync.txt、release.txt | 真实独立模拟渠道/受控A资格：M1/C1/M2及Outbox原子性、timeout/丢响应/通知、明确FAILED退避多attempt/5次告警继续、UNKNOWN原键、租约续租/ACK/retry实际行锁/token/intent围栏、新JVM原键恢复、冻结版本追补/严格签名回执/乱序/高版本完整查询/异绑定隔离、释放回滚/并发/证明核验/后来guard、实际HTTP权限及审计幂等。4014条旧完整保护记录变化0 |
| target/refund/<前缀>-browser/report.json、browser.json | 实际B HTTP（资格受控）、本人/运营退款及核对、桌面/390px无溢出及pageErrors0、GET刷新业务写0；服务器提交后响应丢失，刷新沿原body/operationId得到原结果。测试凭据已删除，不随Git |
| target/b03-readiness/<前缀>-none/report.json、reconciliation-recover-conservation.json | 实际A/TLS/签名MQ：全3B成员无人付，自然到期全名单、原close/complete丢响应新JVM；收款0/退款0，各一次RESERVE和RELEASE，无refund，无CONFIRM；商品完整流水与账户一致 |
| target/b03-readiness/<前缀>-partial/report.json、refund-sync-recover-conservation.json | 实际A自然到期3B成员部分付款，原90.00成功收款/可信FAILED；只停自有A，新B无RPC/MQ全退90.00并释放，新B原证明重放；新A签名MQ/认证Event.query和Trade.query恢复同步。3单各一次RELEASE，sold不变，原支付及Outbox字节保持 |
| target/b03-readiness/<前缀>-completed/report.json、reconciliation-completed-conservation.json | 实际A全3B成员窗口内渠道成功共270.00，最后原支付事件延迟至自然RECONCILING后到达，COMPLETED胜出，只清自己的核对阻断；3CONFIRM/3PENDING，零refund/零RELEASE，保留原收款 |
| target/b05-joint/b056-20261011-quota-01/report.json | 独立verification管理员只读A隔离库，精确限定上3团队与各3原B订单；target=3、冻结成员=3，剩余名额/实际未取消数、paid_count/PAID记录分别NONE0/0、PARTIAL1/1、COMPLETED3/3，终局FAILED/FAILED/COMPLETED。B运行账号仍无A库权限，不以管理员查询替代实际RPC/MQ验收 |
| target/refund/<前缀>-final/report.json，target/payment-closing、settlement、fulfillment/<前缀>-*-regression/verify+recover.txt | 原关闭根竞争/UNKNOWN/已付胜出/迟通知原paidAt、消息与团队冲突/重复原义务、可信成团及后来guard、新JVM回归全部通过，旧保护变化0；全库只读B04证明审计零违规及普通默认实际启动通过 |
| target/b05-joint/b056-20261011-delivery-02/report.json、docs/tests/b05-joint-acceptance.json | 文档收口后最终只读复核与可跟踪脱敏摘要：所有同包报告/原证据hash、实际HTTP契约、精确48表DML、V1～V18冻结、普通包无Flyway/verification且Java21/A契约Java8、外部A原包/契约/既有差异、B04干净、主目录只D26～D28行；.5保护和每个新套件阶段前事实保持 |

本批未将受控A/修改新样本渠道paidAt的超窗故障伪称真实A异常退款；真实A覆盖的是上述三个团队。无“取消后新收款正向全链已通过”结论：普通渠道close tombstone拒绝迟到create/choose由原关闭回归验证；受控窗口内PAID/A CANCELLED由新SQL验证保守隔离。ALREADY_RELEASED未开放的正向异常生产按D27交接，不用修改历史资金或捏造资格完成矩阵。没有新业务失败批次被覆盖；build01新增SQL关联问题在执行前发现并由build02候选修正。原阶段失败/暂停报告全部保留。

### 15.3 B-06交接及复现

[b05-b06-handoff.md](b05-b06-handoff.md)是下一阶段唯一交接入口，列明实际Git/产物/迁移、启动与持久恢复开关、运营查单/重试边界、配置/证书/权限及监控备份部署待办。D26～D28已写双路线图；主目录只更新本次插入行，其余原字节保持。B-06未开展，不因交接而自动部署/提交/合并/推送。取消后异常收款正向资格未启、通用解除REVIEW/逆向履约/真实第三方资金均不冒充已支持。

复现（新批次，不复用旧凭据或报告；写库串行）:

```powershell
./docs/tests/run-b05-joint.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName b056-<新批次>
python -B -X utf8 docs/tests/collect-b05-quota.py --joint-batch b056-20261011-01 --run-name b056-<新名额只读批次>
python -B -X utf8 docs/tests/collect-b05-joint.py --run-name b056-<新最终归档批次> --joint-batch b056-20261011-01 --sql-batch b055-b056-20261011-01-sql --actual-batch b055-b056-20261011-01-partial --none-batch b055-b056-20261011-01-none --completed-batch b055-b056-20261011-01-completed --reconciliation-batch b055-b056-20261011-01-reconciliation --regression-prefix b055-b056-20261011-01 --startup-batch b055-b056-20261011-01-startup --browser-batch b055-b056-20261011-01-browser --audit-batch b055-b056-20261011-01-handoff --quota-batch b056-20261011-quota-01 --protected-after target/refund/b055-b056-20261011-01-final/after-protected.txt
```

新联合批次应同步替换所有子批参数；--publish-summary只在通过后更新脱敏跟踪摘要，不提交原始target。只读名额工具需本机容器管理员能力且固定A隔离库，本机凭据外部注入；不改变B运行账号授权、不访问生产库。清理仅本轮browser-private.json和工具生成的Python缓存，自有端口/环境/默认Java恢复，共享中间件/外部A50051保留。Git仍b-05/53ad32d，.0～.6全部工作未提交。
