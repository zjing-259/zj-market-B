> 最新Git状态（2026-10-10）：用户授权后，B-04.0～.6及通知租约P2补修已提交为`1b5242ed1d34722dba52b84a3962e6dc3abb41b2`，已快进合并master；origin/b-04与origin/master首次推送成功，远程核验均为该提交。b-04已关联origin/b-04。本次文档状态记录随随后文档提交同步两分支；下文“未提交/未合并/未推送”均为各次开发验收当时的历史状态。当前工作树仍为D:/Java/zj-market-b-04；B-05/B-06未开展。

# B-04开发过程：模拟支付、成功成团与待履约

更新：2026-10-10（Asia/Shanghai）。当前工作树：`D:/Java/zj-market-b-04`；分支：`b-04`；创建基线：`7cef24165a12fe443703142225c3dda5fd692a87`。

本文件是B-04唯一开发过程文档，集中维护选择、设计、接口、迁移、实施、验收证据、遗留和交接。[development-roadmap.md](development-roadmap.md)维护整体进度、阶段依赖及入口；后续每次工作须同时维护这两份文档，详细记录不复制成两套。B-05/B-06另建对应阶段过程时，B-04的交接与延期项仍在本文件和路线图保持可追溯。

## 1. 当前任务、授权与状态

当前授权：完成模拟通知写回租约P2补修并维护持久化文档，最新补修见第16节。B-04.0～.6已按模拟范围完成；最终同包联合验收、故障边界与交接见第15节，B-05接续入口为[b04-b05-handoff.md](b04-b05-handoff.md)。D1～D7沿用，无本阶段新增待决方案；B-05/B-06尚未开发，不声明失败退款或真实资金/部署全流程完成。

- B-01基础、B-02、B-03及D6补修已按各自范围完成并归档；生产部署等遗留按B-06验收。
- B-04.0已完成：新工作树独立构建、双库V9及最小权限、真实A/RPC/MQ、D6默认/自定义、占位/关闭跨进程恢复及多用户样本通过；证据和限制见第9节。
- B-04.1已完成联合设计，见第10节；B-04.2已完成，见第11节；B-04.3已完成，见第12节；B-04.4已完成，见第13节；B-04.5已完成，见第14节；B-04.6已完成，见第15节；B-05/B-06待开展。
- 当前改动包括前轮历史校正/.0/.1文档及后续.2～.6源码、前端、迁移、验收工具和文档；产物/凭据继续忽略。尚未提交、合并或推送。后续提交状态须在操作后按Git更新，不沿用旧阶段授权。

## 2. Git基线与历史状态校正

2026-10-10本次核对git log、branch、show-ref及工作树状态；修改前b-04干净，HEAD为7cef241。此前创建b-04时已fetch最新origin/master，远端未发现b-04；本次未再次联网检查远端，以下origin引用为本地跟踪引用。

| 归档对象 | Git事实 | 历史描述的读取方式 |
| --- | --- | --- |
| B-02业务及文档 | 9d75f82、dd59938已在当前历史 | 原目录只有初始工程、源码与唯一文档分置、未提交等是当时状态 |
| 七模块整理及评审补修 | d9f12c7、f93c861；主分支归档36dbc6b | b02-noFileUpdate是实施工作树，整理/补修已包含于当前基线 |
| B-03与D6补修 | 交付7cef241，master/b-03及本地origin/master、origin/b-03均指向该提交 | b03→b-03更名、未提交/未合并及只同步主目录路线图是历史过程，不代表当前未落地 |
| B-04接续 | 本地新分支b-04，工作树D:/Java/zj-market-b-04，基线7cef241；无上游关联 | 不把本地建分支视为已推送；其他工作树不由本次文档修改自动同步 |

修正原则：直接更新首页与当前状态入口，给历史文档和恢复记录增加明确的历史范围说明；不把所有旧路径批量替换成新路径，不改原验收日期、报告位置、测试数量、失败记录或SHA256。原.local/target/node_modules不受Git归档复制，不以Git提交证明新工作树已重新验收。

## 3. 权威资料与固定边界

- 总体阶段与验收：[路线图第20节](development-roadmap.md#20-b-04模拟支付前置选择及实施阶段)，小阶段以20.3为准。
- 已有实施及D6：[B-03过程第19节](b03-development.md#19-b-03剩余收尾补修2026-10-10已完成)；资金接续：[b03-payment-handoff.md](b03-payment-handoff.md)。
- 现有本地结构/接口：[联合设计](b03-joint-design.md)、[B-03 HTTP契约](b03-http-api.json)、[B-02过程](b02-development.md)、[B-02 HTTP契约](b02-http-api.json)。
- A协议：[A/B契约](../../group-buy-market/docs/ab-api-contract.md)为唯一权威，不在B复制协议或透传后台核对RPC。
- 沿用[七模块规范](project-layout.md)、JDK21/Boot4.1.1/Netty4.1.118.Final、独立Jackson2签名与HTTP Jackson3、MyBatis显式事务、Vue3/TypeScript6.0.3/Vite；A与终端Java8规则保持。
- 单SKU、数量1、CNY、最低实付0.01；金额取原订单/A确认冻结事实。首版为明确标注不产生真实扣款的B内模拟渠道，不新增支付微服务或第三方商户接入。
- 旧V1～V9保持不改写，新增迁移从V10及后续实施；先隔离库验收后受控部署，runtime按表DML，普通启动不迁移。

## 4. 已确认选择与待决策项

| 编号 | 用户选择与来源 | 约束 |
| --- | --- | --- |
| B04-D1 | 路线图20.2：失败只终结本次尝试 | 订单/HELD保留，期限内可重试或取消；失败不作为全单未付关闭证明 |
| B04-D2 | 路线图20.2：B内独立持久模拟渠道，由后台通知/查单推进商城 | 渠道和商城分开提交，保留丢响应/通知及恢复窗口 |
| B04-D3 | 路线图20.2：成团转已售并生成待履约 | CONFIRM及待履约幂等；本阶段不实施发货/收货 |
| B04-D4 | 本对话2026-10-10用户明确选择：一个商城支付单下保留多次渠道尝试 | UNKNOWN核对原尝试，明确失败后才新尝试；同订单最多一笔成功支付，不改价/续期；具体标识与约束在.1设计 |
| B04-D5 | 本对话确认：仅verification隔离工具注入故障 | 普通商城不增加延迟/丢通知/未知/改时间测试接口；普通收银台仍仅成功/失败 |
| B04-D6 | 本对话确认：本阶段持久接收并生成待处理工作，由B-05接续执行 | 可信失败/待核对事件与Inbox/工作同事务提交后ACK，不依赖MQ保留期，不提前释放或伪报退款完成 |
| B04-D7 | 本对话确认：每次创建尝试/选择结果前查A，数据库时间记录渠道事实并校验窗口/偏差 | A不可用、时钟矛盾或临近截止无法可靠判断时暂拒新付款并继续后台核对；不修改历史paidAt |

模拟收银台只提交本人尝试标识、成功/失败选择与幂等操作键；金额/币种/paidAt/身份由服务端确定。B03-D11～D13继续有效：已付待成团仍HELD并限制同SKU复购；成团库存确认完成后解除；失败全额退款及库存释放完成后才解除。

D5～D7均已逐项确认，细化边界及参数见本轮联合设计。支付尝试模型D4不重复询问；本轮状态/锁序/接口/迁移及参数交付见[联合设计](b04-joint-design.md)，设计校验见第10节；.2实现与后续未实现边界见第11节。

## 5. 小阶段、依赖与完成门槛

| 阶段 | 目标 | 依赖 | 验收门槛 | 当前状态 |
| --- | --- | --- | --- | --- |
| B-04.0 | Git/D6/支付交接、配置/数据库/有效样本和过程文档 | 已交付B-03 | 基线和实际产物可追溯，隔离环境可重复使用 | 已完成，独立批次b040-20261010-01及-live通过；见第9节 |
| B-04.1 | 支付/尝试/模拟渠道状态、开放与关闭互斥、锁序、消息、HTTP及迁移设计 | .0；D1～D7已确认 | 每个UNKNOWN可恢复，旧冻结close不改写，竞争有唯一裁决 | 已完成联合设计/6项HTTP增量/迁移及故障矩阵校验，见第10节 |
| B-04.2 | 本人收银台、稳定支付意图/尝试及独立渠道记录 | .1 | 双击/丢响应原键恢复，结果竞争唯一成功，关闭/越权拒绝 | 已完成：56项JUnit、HTTP/MySQL/跨进程恢复、真实A、Edge及受影响回归；见第11节 |
| B-04.3 | 可信渠道通知/查询、商城事实与独立交易Outbox/Inbox、A结果及补查 | .2 | 原事实幂等、提交后ACK丢失可恢复、Broker ACK不冒充A接受 | 已完成：V11/统一核验/原Outbox/独立结果与补查/D6持久工作，68项JUnit及真实A/MQ/Edge/恢复回归通过；见第12节 |
| B-04.4 | 停新支付、原渠道关单核验、冻结未付证据和原关闭路径扩展 | .2/.3 | 成功与关闭互斥，UNKNOWN不声明未付/不释放，未开放回归保持 | 待开展 |
| B-04.5 | 团队事件/补查、库存确认/流水/guard/待履约同事务和结果页 | .3/.4 | 早到等待依赖，重复不多确认，不可信资金不履约 | 待开展 |
| B-04.6 | 真实A/B/MySQL/MQ＋模拟渠道＋页面、重启/竞争及B-05交接 | .2～.5 | 独立批次与产物证据、资金库存守恒、失败/核对事件不丢；只称模拟资金验收 | 待开展 |

详细矩阵以路线图20.4～20.7为准，阶段状态与该表同步。完整核对名单、失败退款自动执行、未知退款恢复及退款后释放归B-05；B-04必须持久承担或明确隔离接管相关事件，不ACK丢弃、不提前释放或伪报退款完成。

## 6. 涉及模块、依赖与风险

| 模块 | 后续预计涉及 | 关键约束 |
| --- | --- | --- |
| domain | payment/订单资金规则及端口、成团库存/待履约协调 | 纯Java，不依赖Spring/A SDK；资金、A状态与库存分别表达 |
| infrastructure | 既有MyBatis及新增JDBC显式仓储/迁移、独立模拟渠道、交易MQ及签名/查询适配 | 分离渠道/商城事务，网络/模拟渠道端口调用在本地业务事务外 |
| trigger/api/app | 本人HTTP、后台恢复/消费入站、响应与配置装配/开关 | 本人权限及参数白名单，开关关闭时后端拒绝选择 |
| frontend | 收银台、订单资金/成团/待履约展示 | 不接受前端资金事实，不自动换键重发未知写操作 |
| verification/测试 | 隔离故障、并发、实际A/MQ/MySQL与浏览器证据 | 不把受控故障加入普通资金入口，不把模拟资金称真实扣款 |

依赖与风险：.0已核对新工作树外部配置/权限并建立本轮样本；A活动/团队有期限，后续资金验收仍须按新批次重新确认有效性。支付开放标记必须在渠道调用前提交，与取消同一并发边界；UNKNOWN保留HELD/guard。统一既有用户→商品→guard→库存→订单→预留→协调任务的相对锁序，新增资金/事件锁位置在.1确定。消息业务去重不能只靠eventId；同版本异事实需核对。A窗口与paidAt判定、成团早到、A拒绝后的退款义务、TEAM_FAILED/RECONCILIATION_REQUIRED接管均须明确恢复责任。

## 7. 前次文档工作记录与验证（2026-10-10历史任务）

- 已完成Git历史与当前引用核对，修正路线图总览、B-02/B-03当前状态、启动/目录规范及支付交接；B-01历史验收文档与B-03联合设计注明历史范围；session-handoff顶部改为当前B-04入口并归档下方历史记录。
- 已建立本文件，记录D1～D4、剩余选择、.0部分落实、模块/依赖/风险及按20.3的后续门槛；路线图同步相同状态与维护要求。
- 文档检查通过：git diff --check无错误；本次13份Markdown改动，新增64处本地链接目标存在，原13处SHA256指纹完整保留；无业务源码/契约改动、无暂存。B-02/B-03 HTTP JSON解析通过，分别18/17项操作、316/260处本地引用全部解析；D1～D4及阶段状态已人工交叉核对。检查不等同业务测试或完整Markdown/OpenAPI规范验证器验收。
- 本次未运行构建、数据库/RPC/MQ/浏览器验收或迁移。此前主目录离线构建因缺少surefire-junit3:3.5.6缓存失败，不计作B-04新工作树测试，也不据此否定B-03历史验收。
- 下一步需用户后续指令后核对.0环境/样本，再开展.1联合设计；当前尚不编码、不新建资金表或开放模拟支付。

## 8. 前次文档任务实施复杂度

本次文档接续复杂度低：Git事实核对→当前与历史状态分离→建立唯一过程文档→路线图/入口联动及文档校验。没有改变业务实现或验收结论。B-04整体复杂度高，按第5节依赖逐步推进；.1再拆支付/尝试模型→开放/关闭状态机→锁序/DDL/接口→故障矩阵，.3/.4/.5按路线图第21节继续细分。各步通过对应门槛才更新完成状态。


## 9. B-04.0基线与接续（2026-10-10已完成）

### 9.1 实施范围和实际基线

按Git/交接→显式本地配置→独立构建→数据库与实际通路→样本/恢复→证据/文档六步完成。B仍为7cef241、b-04工作树；A为8c0a3faee01d20730f05c7a357a491bb4438027f。复用现有隔离MySQL/Redis/MQ及A已构建产物，不修改A源码/契约，不升级框架或依赖。

从D:/Java/zj-market-b03显式复制两份既有DPAPI数据库凭据和b02-test-keys公私钥至本工作树被忽略.local；先验证Git忽略规则，同机同用户可解密。未复制旧target/node_modules或历史用户批次。A配置仍外部读取group-buy-market/docs/dev-ops/ab-v2/.local/app.env、b.env；秘密不写命令、持久文档或Git。

新批次：target/b04-baseline/b040-20261010-01；真实通路与样本：target/b03-readiness/b040-20261010-01-live；底层环境：target/environment-probe/b040-20261010-01-live-baseline。复用脚本名称中的B-03/B-01表示既有验收工具，结果归本次B-04.0，不重写旧阶段证据。总报告report.json为PASSED，provenance.json记录本轮B/A提交、A契约/包、B产物、锁文件和V1～V9 SHA256。

### 9.2 验证结果与证据

| 检查 | 本轮结果 | 证据（均为本工作树忽略目录） |
| --- | --- | --- |
| 后端与D6单元基线 | JDK21.0.2、七模块打包及46项测试通过，0失败/错误/跳过 | 基线目录build.log；app/target/surefire-reports |
| 前端 | 按锁文件npm ci，vue-tsc及Vite生产构建通过；锁文件未变 | npm-ci.log、frontend-build.log |
| 普通包 | 普通exec实际JDK21启动通过；不包含verification/Flyway | normal-runtime.log、normal-package.txt |
| 双库与角色 | 开发zj_market及验收zj_market_b02_test均V9，Flyway验证通过且migrationsExecuted=0；runtime仅21张B表DML，DDL/history/A/system/grant拒绝；migrator仅本库DDL等权限 | live目录两组*-migrate.txt、*-verify.txt |
| RPC/MQ/签名 | 真实A Java8、B Java21，TLS签名查询及错误签名拒绝、授权消息收发、越权发布拒绝、结果签名及持久结果查询通过 | live/baseline.json及底层环境report.json、依赖树 |
| 本人/运营、商品与A准入 | 真实登录/越权、4商品版本1同步、报价90.00、开团/JOIN/满团/过期/资格、CLOSE_MARKER阻断迟到reserve通过 | live/verify.txt、fixtures.json、live-fixtures.json |
| 占位/关闭恢复 | 真实A已提交后丢响应，完整B新进程原query恢复；关闭原hash不变、每单一次RELEASE；最终库存10可用/0预留，守卫释放 | live/trade-recovery.json、close-recovery.json、close-recover.txt |
| D6实际装配/落库 | 默认300000ms及自定义60000ms均经真实Spring/HTTP/MySQL验证；D9仍300000ms，含原键/并发/原子回滚等本地订单检查 | d6-default.txt、d6-custom.txt及对应日志 |
| 未开放支付关闭回归 | 修正临时测试编排后通过；原失败保留见9.4 | closes-retry.txt、closes-retry.log |
| 恢复与交付 | 本批A/B退出，50051/18091/18092/5173释放；进程环境恢复、默认Java8保持；产物指纹全程未变，302份交付文件/16份已知敏感值扫描零命中，已跟踪应忽略文件0 | live/cleanup.txt、基线report.json、delivery-audit.json |

普通app SHA256：`E046FC85D49573A2F4D944697746745750A97D118FD3C07BAE80696B7B9EEF2E`；verification SHA256：`CEC3456059835BE5E25090401A96F1628B36FDFFDBD55EE1ECF20B68D6E96E53`。A契约SHA256：`83B02A7EBF5E80B5EF4D1B03936E6B1CA33EED32F6D9C68B451E855C6192D7DD`。这些是本轮重新构建/读取结果，与旧43项及D6收尾46项批次分开保存；不要求不同构建一定具有不同哈希。

### 9.3 样本与后续使用方式

本批创建4名普通用户（USER/MEMBER/SECOND/THIRD）及1名运营OP；账号密码仅在.local/b03-b040-20261010-01-live.credentials.xml中DPAPI保存，用户/商品/活动关联由live/fixtures.json查询。open商品c53e9213-d39f-4e0d-a94b-cfecd1c725e4、活动772888814511，版本1，原价100.00/CNY、A实付90.00、目标人数3；已有10件经运营接口入库。另有满团、过期和资格限制样本；除open已实际入库外，其他fixtures中的inventoryPlan仍只是计划，不把inventoryApplied=false误读为已入库。

活动样本创建于本机2026-10-10约11:19，正常活动结束时间为创建时起1天；已建团队付款期限另见live-fixtures.json，不按活动截止推算。两个B实际订单已在关闭恢复验证中关闭，最终open库存10可用/0预留；不是待支付订单，更没有资金或成团确认。工具另有直接A占位的团队，不能直接用它作为所有成员均有B资金记录的成团验收样本。

后续.1/.2使用前先重新报价及核对活动/版本/库存/账号；成团资金验收必须通过B用完整至少3名普通用户新建团队和订单，不能复用含直接A测试占位的旧团队。过期时用新RunName准备新批次，不改旧活动/订单期限，不清未知历史库存，不复制旧报告冒充新验证。

### 9.4 失败、范围与观察项

补充关闭回归首次失败发生于临时PowerShell编排：将原本不存在的B_ORDER_RESERVE_WAIT_MILLIS以空字符串恢复，Spring无法解析long，尚未进入业务验证。失败日志closes.log和closes-first-failed.txt保留，原因见closes-first-failure-reason.txt；移除该环境项以恢复默认后重跑通过。共享b-runtime.ps1已有Restore-BEnvironmentVariable正确处理空缺，本轮业务/脚本源码无须修补。

既有Hessian/JDK21 BigInteger反射告警仍可复现，实际TLS签名RPC与恢复通过，保留观察，不通过框架升级掩盖。此前主目录离线缺Surefire缓存的失败属于旧记录；本轮在线Maven构建已通过。普通包启动时外部集成关闭的检查不能替代完整商城通路，后者由本批live验证独立证明。

本轮未新增V10或资金表，未改写V1～V9；显式执行现有migrate入口仅校验已应用迁移（执行数0），其权限探针创建/移除临时表；普通应用启动仍不迁移。未运行全套B-03.6/Edge浏览器、实际A停启故障或模拟支付/退款/成团验收；这些不属于.0完成证明。B-04.1～.6、B-05/B-06仍待开展，D1～D4保持，故障入口/未来事件接管/时钟判定按.1逐项交用户，不默认选择。

### 9.5 可重复入口

在当前工作树PowerShell7、既有被忽略配置及本地服务可用的条件下，先构建新产物，再用唯一新RunName：

```powershell
./scripts/mvn.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -MavenArguments @('-B','package')
Push-Location frontend
try { npm ci --no-audit --no-fund; npm run build } finally { Pop-Location }
./docs/tests/run-b03-readiness.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <新的唯一批次> -WithUnpaidClose -SkipBuild
./docs/tests/run-b03-orders.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -SkipBuild
$previousWait = [Environment]::GetEnvironmentVariable('B_ORDER_RESERVE_WAIT_MILLIS','Process')
. ./scripts/b-runtime.ps1
try {
    $env:B_ORDER_RESERVE_WAIT_MILLIS='60000'
    ./docs/tests/run-b03-orders.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -SkipBuild
} finally { Restore-BEnvironmentVariable -Name B_ORDER_RESERVE_WAIT_MILLIS -Value $previousWait }
./docs/tests/run-b03-closes.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -SkipBuild
```

默认D6验证前须确认该变量不存在；不要以空值替代移除。orders/closes使用固定报告位置，每轮需在下一次运行前复制到本批独立目录；SkipBuild只表示复用本轮已构建且指纹固定的产物，不表示脚本重新执行单元测试。readiness的原键verify只适用基础prepare模式；本轮WithUnpaidClose建立的已受理订单通过原意图/任务路径恢复，不重放prepare或旧INSERT。

### 9.6 本轮复杂度与交接

复杂度中等：不新增业务实现，但涉及两个JDK、双B库角色、真实A/MQ签名、隔离样本、两种等待期限及跨进程恢复；按9.1六步实施并逐项保留证据。可提交改动仍仅文档，未暂存/提交/合并/推送，原主目录和A源码状态未改变。下一步B-04.1联合设计，先确认剩余实质方案再冻结状态、锁序、接口及V10设计，不越过.1直接实现收银台。


## 10. B-04.1支付与关闭联合设计（2026-10-10已完成）

本轮按模型/决策→状态与关闭竞争→锁序/时间/恢复→消息及B-05接管→HTTP/表计划→故障矩阵与校验六步推进，复杂度高。D5～D7逐项由用户确认并立即录入第4节和路线图20.6；不默认选择未答方案。

交付：[b04-joint-design.md](b04-joint-design.md)维护最终设计规格，[b04-http-api.json](b04-http-api.json)维护6项新增本人HTTP及既有订单响应拟扩展；本文件仍为唯一过程记录。CONTEXT.md补充商城支付单、渠道尝试、未付关闭证据和待履约业务定义，保持纯词汇、不放表/锁/实现。

关键结论：稳定paymentId关联原订单且用于A支付事实，多attemptId归同一支付单；未知原键核对、失败后匹配前驱才新尝试。渠道根行锁与持久关闭标记裁决成功/未付关闭，覆盖迟到create；商城先提交可能开放标记，渠道与商城分开事务；旧NEVER_OPENED close永久不改写。成功事实与交易Outbox同事务，Broker ACK与A接受分离；Inbox/工作持久承担D6，B-05接续退款；可信成团/本单成功资金/A接受三者齐备才原子CONFIRM/流水/guard/待履约。

D7默认查询往返/证据有效期/允许偏差各2000ms，普通入口边界保守校验、锁后取数据库时间，历史paidAt不重算；A当前serverTime为系统钟而支付窗口及未来判断使用数据库钟，详见联合设计第5节。锁序/外键隐式锁、独立消费者路由、旧A证据兼容和分阶段开关是实施重点。

新增迁移计划V10支付/模拟渠道基础、V11独立交易可靠消息/待处理工作、V12渠道关闭证据、V13待履约；本轮只写设计，没有SQL迁移文件或数据库变更。HTTP契约明确designed-not-implemented；旧B-02/B-03契约及V1～V9保持。设计校验通过：6项操作、23份schema、123处本地引用解析；11个正例/46个反例（字段白名单、操作键必填、金额/时间/结果枚举等）通过；本次新增链接目标存在、历史指纹保留、旧B-02/B-03契约与V1～V9/A契约未改，git diff --check无错误。报告target/b04-design/b041-20261010-01/validation.json；校验器仅检查本契约所用schema子集，不称完整OpenAPI规范验收。交付敏感值/忽略边界审计见同目录delivery-audit.json。没有重新运行业务测试，不引用.0的46项测试冒充资金设计运行验收。

.1设计门槛已满足，下一步.2才实现V10/支付基础及收银台。具体代码、迁移DDL、实际权限与进程故障证据均在相应阶段落实，不将设计契约标为implemented。锁/证据/迁移调整若涉及新的业务取舍继续交用户，例行实施细节在已确认约束内推进。

## 11. B-04.2模拟收银台与渠道记录（2026-10-10已完成）

按V10/权限→领域与独立渠道事务→持久任务恢复/本人HTTP→收银台→测试/文档推进。普通入口默认关闭；渠道成功暂为待商城同步，.3负责资金事实与Outbox。沿用已开放订单禁止旧未付关闭的保护。重点验证原键恢复、同单多尝试、结果竞争、数据库时间及越权；不改V1～V9，不修改A，不提交或推送。

### 11.1 已落地范围与边界

新增payment领域服务/端口、商城PaymentRepository、独立SimulatedChannel、显式PaymentConfiguration及恢复job、6项本人HTTP和Vue收银台。商城事务提交稳定支付单/尝试/操作/任务及POSSIBLY_OPENED后才调用渠道；渠道拒绝外层事务，根行裁决单次终态，成功槽唯一约束限制同单一笔成功。失败仅终结尝试，HELD与守卫保留，previousAttemptId匹配原FAILED后才能重试；UNKNOWN不换键。结果选择先持久受理，后台查原渠道再决定是否重新查询A执行；租约/意图版本均在业务锁后复查。恢复已发生的渠道事实不要求A在线，也不受收银台写开关影响。

V10新建8表并扩展订单CHECK，运行角色白名单增至29表。首轮V10已执行后，收尾用新增V10.1补充受理快照receipt_hash及历史行摘要回填，不改写已执行V10，更不改V1～V9；摘要使用MySQL规范化JSON表示，读取时校验。HTTP重复JSON字段改为显式Jackson3 factory customizer；对照实际HTTP发现.1契约草稿把既有message误写为info，已修正B-04文档为code/message/data/requestId，过滤器和ApiResponse保持既有格式。已终结同结果的新操作持久APPLIED观察并返回200。

默认B_PAYMENT_ENABLED=false、B_PAYMENT_CHECKOUT_ENABLED=false。已装配支付的环境需保留B_PAYMENT_ENABLED=true及恢复job，只以CHECKOUT_ENABLED=false关闭新写，已有本人查询与任务仍可用。必须同时具备identity/order/trade/inventory/database及真实A配置；不得在普通启动时迁移。时间参数RTT/TTL/skew默认各2000ms，开启时校验1～60000ms；凭据同时检查数据库时间和单调时钟有效期，纳秒往返超限不向下取整放行。过期凭据仅阻止未执行新动作，不丢已持久渠道事实。

本阶段渠道成功只更新尝试观察，商城fundsState保持UNKNOWN、aAcceptance=NOT_SENT、paidAt/successAttemptId仍null，提示PAYMENT_SYNC_PENDING。通知已在渠道事务持久READY，.3才执行可信事实核验、商城成功＋交易Outbox和A处理结果；不声称完成资金入账。已有开放标记时旧取消/超时路径保守拒绝或进入核对，不释放库存；.4再接入渠道关闭证明。待履约及确认库存归.5，.2不生成CONFIRM/RELEASE。普通HTTP与页面只提供成功/失败选择，所有故障均在verification工具。

收银台操作按用户/订单保存在浏览器，只含原键、路径及参数；存储失败不先发请求。重新载入仅GET，404或未知结果不生成新键；手动重试原请求。Web Locks串行化同用户同订单多个标签页；换账号清空页面结果并禁止重放原用户操作。只存操作参数，不存访问/刷新令牌。订单响应增加paymentSummary及null fulfillmentSummary，支付能力由服务端当前状态及期限给出；收银台明确模拟、不真实扣款、渠道成功仍待商城同步。

### 11.2 验证进展

后端56项JUnit（新增10项）、前端类型/生产构建通过；已通过真实HTTP/MySQL、独立渠道事务、同键/异键/相反结果竞争、未知不换键、原操作离线重放、实际行锁等待后租约过期、旧worker fencing及新JVM恢复。真实签名TLS A查询在默认2000ms策略下完成FAILED→同支付单新尝试→SUCCEEDED，未向A发送支付事实，库存HELD；Edge验证响应丢失/读404/刷新不写/原键重试/失败再试/双标签/换账号及桌面手机布局，pageErrors=0。最终同产物批次及权限/回归证据见11.3；中间批次与最终验收分开保留。

### 11.3 最终验收与产物

最终源码归位后七模块打包通过，56项JUnit（原46项＋支付10项）、0失败/错误/跳过；前端vue-tsc/Vite通过，锁文件未改。收银台序号按HTTP契约用字符串；CLOSE_MARKER无付款期限时本人查询正常，新写在锁内持久拒绝且不调用A。公开返回模型单独放model.valobj，仓储/渠道接口分别放adapter.repository/adapter.port，service/impl分包；普通包不含verification/Flyway，无旧PaymentModels/接口孤儿class。新支付仓储使用已有Spring JDBC/DataSource/事务组件显式参数化SQL，既有MyBatis DAO不改，不增加依赖或越层引用。

| 验收 | 最终结果与证据 |
| --- | --- |
| 后端/前端 | target/b042-build-layout-final.log及app/target/surefire-reports；target/b042-browser-frontend-build.log；56项测试与生产构建通过 |
| 本人HTTP/渠道/竞争 | target/payments/b042-20261010-layout-final/verify.txt、verify.log：6项HTTP，匿名/他人/Origin/未知及重复字段/no-store/requestId/GET无写；同键和异键创建竞争、相反选择竞争、同结果绑定/终态200、FAILED重试稳定paymentId、UNKNOWN原键保留、成功不可反转及DB单成功约束通过 |
| 事务/恢复/摘要 | 同目录recover.txt、recover.log、restart.json：独立渠道成功先提交；实际业务行锁等待跨租约后旧writer无更新；原token/intent fencing；受理快照篡改探针回滚；实际第二JVM在A离线/新写关闭时查原渠道恢复，不重算paidAt，不产生RELEASE/CONFIRM |
| 真实A及时间 | target/b03-readiness/b042-20261010-live-layout-final/payments.json、payments.txt：实际Java8 A/TLS签名query、数据库时间及默认RTT/TTL/skew=2000ms，通过FAILED→重试→SUCCEEDED；A支付事实发送0，商城UNKNOWN，库存HELD |
| 双库/角色/迁移 | live目录两组*-migrate.txt证明两库均10.1、11份迁移验证通过、最终migrationsExecuted=0；收尾发现development仍为原21表授权，显式运行既有provision补齐，不覆盖原报告，最终payments目录database-boundary中两库*-verify.txt证明runtime仅29张B表DML、DDL/history/A/system/grant拒绝；migrator仅本库维护。V10首次执行证据target/payments/v10-first-test-application及live-01；V10.1首次执行证据b042-20261010-accepted及live-accepted，不覆盖这些首次报告 |
| Edge | target/payments/b042-browser-20261010-layout-final/browser.json、browser.log、cashier-desktop.png、cashier-mobile.png：丢写响应/模拟读404/重新载入不写/原键手动重试/失败再试/双标签共享原键/换账号不重放/令牌不落Web Storage通过；pageErrors=0，手机无横向溢出，截图已查看 |
| 既有订单/未开放关闭 | target/payments/b042-orders-layout-final.txt、b042-closes-layout-final.txt及对应target/b042-*-layout-final.log：原订单原子预留、D6默认等待、旧未付取消/超时/关闭恢复/fencing等受影响回归通过 |
| HTTP/交付边界 | 同最终payments目录contract-validation.json：6项操作、23份schema、123引用、11正例/46反例及7份实际HTTP响应通过；V1～V9与.0工作区SHA256逐一相同，B-02/B-03/A契约未改，新增文档链接/历史指纹检查通过；只称所用schema子集校验 |

总报告：target/payments/b042-20261010-layout-final/report.json。普通app SHA256：`B8B0961B080B2B48FDE8EB4BBCBAAA4328FFD5F641FD9E0A08F48E8DB35F7D73`；verification SHA256：`403946AE8974EFDCD6B18E6407FBB6882EE0A98B36996AD270860DDFAC29E75A`。前端构建、迁移及最终产物指纹另见报告。最终A/B和前端验收进程退出，50051/18091/18092/5173释放，真实通路报告确认调用者环境和默认Java8恢复。Docker首次发现已停止，恢复既有Docker后使用原mysql/redis/MQ容器；未停止共享中间件。敏感值/忽略边界审计见同最终payments目录delivery-audit.json：332份交付文件、46项已知敏感值检查通过，无敏感匹配或被跟踪的忽略文件；Git差异格式检查通过，主目录B及A仍干净，依赖锁文件和A契约指纹保持。

### 11.4 中间失败与接续限制

首次迁移调用因Docker daemon停止而在任何SQL执行前失败，恢复后通过。中间工具编译有复合var声明及包归位漏改Accepted导入，均修正后重新构建；第一次浏览器脚本登录按钮有两个同名定位，改为表单提交按钮后通过。真实HTTP发现重复JSON配置属性未生效，改显式factory customizer；契约对照发现.1的info误写及attemptNo类型偏差，依当前仓库message字段与契约字符串序号修正并重新捕获响应。文档验证曾直接比较Git LF与Windows工作区CRLF，改为同时检查Git内容及.0原工作区SHA256；未改历史迁移。中间日志仍在target/b042-*及各独立批次，最终只以上表的绿色批次为准。Hessian/JDK21 BigInteger反射告警仍观察，实际TLS/RPC通过，未升级依赖或改变A。

本轮新建独立账号/商品/活动/订单样本，未清库、未改未知历史库存、未续期。最新实际A样本标识与paidAt见live-layout-final/payments.json；该订单已有真实模拟渠道成功，商城仍UNKNOWN、A仍未付款，HELD/守卫和READY通知必须保留供.3接续。活动/团队到期可能改变A状态，后续先查原渠道及A原订单，不把超时当失败、不重写paidAt；新闭环验收使用新批次。真实readiness另有直接A占位及JOIN样本，不是所有成员均有B资金的完整团队，不能据此声称成团资金验收。

.2完成仅表示模拟收银台和持久渠道基础达标；普通入口仍默认关闭。下一步.3建立统一可信事实核验、商城成功＋交易Outbox、通知ACK、A处理结果/补查与D6持久Inbox/工作接管；.4才接通已开放取消/关闭证明，.5才CONFIRM及待履约，.6才完整联合资金故障验收。B-05退款不执行、不伪报完成。无新增待决方案，不提交、合并或推送。复杂度高，按本节分层实施并逐项保留隔离/真实/浏览器证据。

### 11.5 重复验证入口

先显式选择B JDK21构建，以下各RunName须全新；这些脚本创建本批隔离样本，不能重用旧INSERT或修改旧窗口：

```powershell
./scripts/mvn.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -MavenArguments @('-B','package')
npm run build --prefix frontend
./docs/tests/run-b04-payments.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <新的资金批次> -SkipBuild
./docs/tests/run-b04-payments-browser.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <新的浏览器批次> -SkipBuild
./docs/tests/run-b03-readiness.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <新的真实A批次> -WithPayments -SkipBuild
./docs/tests/run-b03-orders.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -SkipBuild
./docs/tests/run-b03-closes.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -SkipBuild
```

WithPayments与WithUnpaidClose/WithJointFaults互斥，不能用旧未开放关闭工具取消已暴露订单。脚本严格限定验收库/运行角色，故障bean和直接探针只存在verification；浏览器短期凭据文件退出后移除，A/DB凭据继续由既有.local/外部配置读取，不输出秘密。orders/closes及database固定报告需串行执行并在覆盖前复制到独立批次，避免证据相互覆盖；SkipBuild只复用本轮已构建产物，不表示重跑JUnit。


## 12. B-04.3可信模拟事实与可靠通知（2026-10-10已完成）

授权：开展可信模拟事实与可靠通知，沿用D1～D7。基线b-04/7cef241及未提交的.0～.2成果保持，不提交/推送。计划：V11及统一渠道核验→资金成功＋原Outbox原子提交→独立签名MQ/RPC结果及查询补偿→D6团队原文与每订单工作持久接收→故障/真实通路/回归及文档。复杂度高；主要风险为错误资金关联、重复或乱序覆盖、Broker ACK误作A接受及缺本地订单丢事件。普通入口默认关闭，.4关单证明/.5履约仍未实现。不修改已执行V1～V10.1、A协议及依赖版本。


### 12.1 实施范围与事务

新增纯Java SettlementService、ISettlementRepository/ISettlementTransport/IChannelFacts及单文件值对象，基础设施SettlementRepository/TradeMessageReader/RocketMqSettlementTransport、trigger SettlementJob、app SettlementConfiguration。既有支付恢复任务保留，旧任务完成不能把SUCCEEDED降回UNKNOWN/UNPAID。新配置B_TRADE_EVENTS_ENABLED=false；普通支付新写仍默认关闭，未开放完整闭环。

通知与查原渠道共用observe：原根snapshotHash/requestHash/金额/CNY/期限/成功指针/流水及paidAt核验，同业务锁序保存成功事实/摘要、支付指针、订单PAID_WAITING_A及一份固定PAYMENT_SUCCEEDED Outbox。渠道独立事务及ACK保持分离；同事实重复不新增eventId，不按当前期限丢弃旧paidAt。异常窗口/订单冲突保存SUCCEEDED、WAITING_REFUND和唯一DEFERRED_B05义务，不发正常付款；临时核对标记不直接推导退款。通知正文/hash与原查询交叉验证；读补偿按检查时间公平轮转，不因前20条长期未知饿死后续记录。

V11只新增五表及新字段，不改已执行V1～V10.1；原字节LONGBLOB防止JSON重排破坏签名。显式迁移/角色仍由verification维护；runtime仅34张B表DML，无history/A/system/DDL/GRANT，普通app不迁移。短事务认领仅锁任务/Outbox，随后业务事务先完整业务链、最后Inbox/Outbox/游标/工作并校验令牌及锁后数据库时间；跨租约旧writer不更新。退款义务增量原因使intentVersion增加，B-05可识别新证据。

### 12.2 可靠投递、A接受及D6

固定原event/body/hash/occurredAt，HMAC签名使用原字节与物理Topic。首次READY发布不依赖A在线；发送未知恢复先查原结果，查询故障仍可重发原字节；PUBLISHED≠ACCEPTED，持续缺结果查询重试/第5次alerted及原事件重发。失败1/2/4/8分钟后8分钟；通知2/4/8/16/30秒加抖动，第5次告警工作，租约30秒；服务2秒/20条扫描。恢复不受CHECKOUT_ENABLED=false影响。

使用已有ACL组B_INTEGRATION_RESULTS-dev及B_TEAM_EVENTS-dev，独立于B_PRODUCT_SYNC_RESULTS-dev；未改共享ACL、A凭据或A源码，.1建议组名非硬编码要求。交易结果/团队消费者严格校验原HMAC、Topic/tag/Key/source/channel、重复/未知字段、schema和嵌套资金。商品组验公共结构后有意分流已知交易类型，不隔离有效支付结果。非法正文先隔离，隔离失败抛出、客户端重试且maxReconsumeTimes=8；本轮不复用商品组或消费者状态。

A结果关联原eventId→Outbox→payment/order→Aorder/team和完整支付事实；REJECTED保留成功资金并合并唯一退款义务，不换eventId重算。queryEventResult的NOT_FOUND/WAITING_DEPENDENCY不是拒绝；完整Trade.query支付证据可补偿。既有布尔A快照不造历史paymentId/paidAt，完整资金证据另存Inbox，校验后按版本更新原展示快照/hash；迟到回执不得倒退。

团队事件Inbox、原始名单/版本/核对标识及每订单工作同事务持久后ACK；缺本地订单/缺A证据WAITING_DEPENDENCY并重查映射，已知失败/核对DEFERRED_B05，成团WAITING_DEPENDENCY留.5。无用户归属不猜用户向A查单；已映射订单继续查询核验。业务工作按source/channel/team/version/order摘要去重，同版本异事实隔离；B-05退款义务paymentId/orderId唯一并合并原因。所有路径仍HELD/guard，不发REFUND_STATUS_CHANGED、不CONFIRM/RELEASE。

### 12.3 验证范围与中间记录

68项JUnit（原56项＋.3新增12项）通过；真实MySQL的M2/Outbox回滚、并发重复、旧任务不降级、租约过期、严格签名结果/重复及同event异正文、早到成团/缺订单、跨事件同团队版本工作去重、A拒绝/窗口外异常/错误金额/同版本名单冲突及独立JVM丢ACK恢复通过。实际A/TLS/MQ的签名付款、独立消费者、Broker≠A接受、完整结果、queryEventResult和Trade.query通过；Edge资金待确认→A确认、刷新不写、手机无溢出通过。最终源码同产物批次、回归、角色/交付审计均通过，以下一节为最终绿色报告。

中间verification工具有生成字符串换行的编译错误，修正后重新构建；未执行失败产物的业务探针。既有Hessian/JDK21反射告警仍观察，实际RPC通过，未升级依赖。初次真实联调的开发角色仍原29表，资金业务只在隔离库运行；最终显式provision补齐开发库34表并独立保存报告，不覆盖旧证据。


### 12.4 最终证据与接续

| 验收 | 通过证据 |
| --- | --- |
| 构建 | target/b043-build-final.log，七模块、68项JUnit/0失败/错误/跳过；前端vue-tsc/Vite构建通过，无依赖升级，package-lock不变 |
| 隔离SQL/恢复 | target/settlement/b043-20261010-delivery-isolated/verify.txt及recover.txt，真实M2/Outbox原子回滚、并发幂等、旧worker不降级、租约令牌、签名/关联/金额/版本冲突、D6缺单/早到工作、唯一B-05义务；第二JVM在checkout关闭/A离线时恢复原资金/原event/丢ACK，无RELEASE/CONFIRM |
| 真实A/MQ | target/b03-readiness/b043-20261010-live-delivery/settlement.json及settlement.txt，实际Java8 A、TLS签名、B付款Topic与现有独立ACL组、真实MQ结果、完整支付校验、queryEventResult与Trade.query；原event唯一，SUCCEEDED＋ACCEPTED，库存HELD；payments.json记录同批.2前置时UNKNOWN，settlement.json才是.3最终状态 |
| Edge | target/payments/b043-browser-20261010-contract/browser.json、http-contract-samples.json、settlement-pending-desktop.png、settlement-accepted-mobile.png；真实B HTTP/MySQL/独立渠道，A接受仅verification控制，待确认→已确认、刷新0次支付POST、手机无横向溢出及pageErrors=0；此前delivery截图同界面已目视检查，最终截图亦按同场景保留 |
| 回归 | target/payments/b043-payments-regression/verify.txt及recover.txt，.2 HTTP/幂等/未知/渠道/关闭保护保持；本最终目录orders.txt、closes.txt及target/b043-orders-regression.log、b043-closes-regression.log通过。旧探针正文V7/V9/21为原测试范围标签，当前迁移/权限以本行下一项实测为准，不据此声称回退库版本 |
| 迁移/权限 | 本最终目录development-migrations.txt、development-permissions.txt及live两组*-migrate/verify.txt；双库当前V11、12份历史迁移验证、最后执行数0；运行角色34表DML，DDL/history/A/system/grant拒绝。首次隔离V11证据target/settlement/b043-20261010-01/provision.log；开发首次V11见live-01/database.credentials.xml-migrate.log；后续只补精确表授权，无清库或改A |
| 契约/交付 | 本最终目录contract-validation.json：6操作/23 schema/123引用、11正例/46反例，13份实际HTTP响应（含UNKNOWN、SUCCEEDED/PENDING/ACCEPTED）通过；V1～V9原.0 SHA不变，V10/V10.1经Flyway历史校验，B-02/B-03/A契约未改；专用schema子集校验，不称完整OpenAPI验证。delivery-audit.json：352份文件/56项已知敏感值检查，无秘密/私钥/令牌匹配、忽略文件未被跟踪 |

总报告target/settlement/b043-20261010-delivery/report.json。普通app SHA256 `F27878A8F53B961C9CFA0B244B1F4FAB8138ACEAE6384A8762E746AED1FB59E3`；verification SHA256 `4C2C8BE211D67C7282EA9922D8130444BCF7ED928D54122F573F1F58E583C24F`。普通包仍不含verification/Flyway；历史SHA及文档链接检查、git diff --check通过。当前b-04/7cef241，未暂存/提交/合并/推送，原B主目录与A工作区仍干净。验收进程退出、50051/18091/18092/5173释放，临时浏览器凭据移除，调用者环境与默认Java8恢复；共享中间件保持运行。

本轮覆盖.3的资金/消息/接管门槛，不声称实际MQ丢结果停启/新组死信全矩阵或完整成团资金验收均已完成；maxReconsumeTimes=8及隔离失败重试边界已实现/测试，完整联合故障继续.6。当前真实样本已模拟付款且A接受、HELD/guard保留，未来TEAM_COMPLETED交.5确认库存；失败/核对交B-05工作，不通过旧未付关闭释放。旧.2未知资金和本轮异常窗口故障样本仍须保留原渠道/paidAt/义务，后续先核对，不重算时间、续期或清除库存。原readiness还有直接A占位样本，不能称整组成员资金均由B完成。

下一阶段B-04.4接通支付开放后的关闭裁决/证明；.5才库存CONFIRM与待履约；.6完成联合故障矩阵。B-05才执行核对/退款，.3不发送退款完成。普通支付/交易恢复装配仍默认关闭，受控启用时必须保留恢复而仅关闭新写。D1～D7未改变，无新增未答方案；现有ACL组名选择为例行实现，不改用户决策或公共授权。

### 12.5 重复验证入口

显式选择B JDK21，所有RunName必须全新；脚本创建各自样本并恢复调用者环境，不复用未知资金订单或旧INSERT：

```powershell
./scripts/mvn.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -MavenArguments @('-B','package')
./docs/tests/run-b04-settlement.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <新的隔离批次> -SkipBuild
./docs/tests/run-b03-readiness.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <新的真实通路批次> -WithSettlement -SkipBuild
./docs/tests/run-b04-settlement-browser.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <新的页面批次> -SkipBuild
./docs/tests/run-b04-payments.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <新的支付回归批次> -SkipBuild
./docs/tests/run-b03-orders.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -SkipBuild
./docs/tests/run-b03-closes.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -SkipBuild
```

WithSettlement隐含WithPayments/TradeRecovery/LocalOrders，只允许prepare新批次；与旧未付关闭/联合故障互斥。database/orders/closes固定报告串行运行并复制到独立目录，不能互相覆盖后冒充原批次。服务恢复允许处理已持久资金，浏览器A确认控制与异常金额/时间/旧租约注入只存在verification；普通接口不增加故障能力。

## 13. B-04.4 支付开放后的关单与竞争（2026-10-10，已完成）

2026-10-10接续：实际工作树D:/Java/zj-market-b-04，b-04/7cef241；.0～.3改动仍未提交，本轮保留全部既有改动。以当前代码、联合设计4.2/5及A契约为依据。旧关闭只能NEVER_OPENED，开放后取消原先409，当前开始接通。

实施计划：V12新增支付根关闭请求/证明及订单关联；复用原交易协调租约，商城先CLOSING并使支付worker失效，事务外渠道根锁裁决；成功沿用M2，未付完整覆盖证明才冻结CLOSED_UNPAID请求，A close→query CANCELLED后原子释放。更新本人取消准入和页面说明，执行真实SQL竞争/跨JVM/未知/旧关闭回归与构建。主要风险为在途选择、迟到create、旧租约、成功通知与关闭交错；资金未知不释放、不向A声明未付。D1～D7不变，.5/.6/B-05仍独立。

以下保留开始实施时的计划；最终验收与完成状态见13.3。

### 13.1 已实现及接续约束

- V12只新增b_payment的根关闭请求/摘要、证明原字节/摘要、covered_attempt_no、channel_closed_at_ms、close_verified_at_ms，b_sim_payment的稳定closeId/请求摘要/原裁决/摘要，及b_market_order证明关联。不增加表，runtime仍34表DML；V1～V11（含V10.1）不改写，原快照及旧close请求不改写。
- Mclose在原订单锁序内先记CLOSING、稳定channelCloseId和完整尝试集（包含尚未发送create），支付任务intentVersion提升并清空旧令牌。原交易任务转CLOSE；停止新尝试/选择。本地不释放，也不提前生成A未付声明。
- 原交易worker在A close/query之前调用prepare。商城短事务取原键/完整尝试及租约，释放事务后先查原渠道关闭裁决；缺失才以同键closeRoot建立阻断，不能把单尝试NOT_FOUND当未付。渠道使用parent SHARE→根→递增尝试锁；成功先提交返回原完整成功；否则根和OPEN尝试关闭，未到达create的尝试也持久为CLOSED_UNPAID，形成完整证明。迟到create只读原终态，迟到选择拒绝。
- 商城锁后重新校验租约、原请求、尝试覆盖、身份/金额/时间/摘要。确认未付后一次冻结证明、首次verifiedAt与原A CLOSED_UNPAID请求；之后所有重试保持同closeId/hash/verifiedAt。A close摘要仍不释放；query CANCELLED后复用原库存余额/预留/RELEASE流水/订单/guard/任务同事务收尾。UNKNOWN按2/4/8/16/30秒＋抖动重试，第5次持久alert并告警，继续原键；矛盾证明原文入quarantine、支付/订单/任务进入核对，不调用A未付close。
- PAID裁决调用既有SettlementRepository.observe（M2），保留原paidAt、成功指针、唯一PAYMENT_SUCCEEDED Outbox，并使待未付关闭的交易租约失效。新增关闭意图本身不构成退款原因；已冻结未付证明/已CLOSED等矛盾仍走原核对/唯一B-05义务，不覆盖旧声明。未付失败只终结尝试。
- 超时沿原任务查询新A结果，只有serverTime达到原paymentDeadline才保存PAYMENT_TIMEOUT意图；渠道关闭/查询及成功恢复不要求新的付款窗口凭据，用户取消不要求到期。
- 支付开放后关闭只在B_TRADE_EVENTS_ENABLED装配资金恢复时启用，复用原trade扫描/租约/暂停与核对保护，不受B_PAYMENT_CHECKOUT_ENABLED=false影响。不具备资金恢复装配时继续旧保守拒绝，避免成功裁决缺少M2接续。普通环境开关默认值保持。
- 本人GET/取消响应共用订单视图，canCancel按服务端真实准入；CLOSING后不再显示新取消入口，原操作键仍可查询/重试。页面说明接受意图不等于最终未付；成功胜出继续支付处理。既有POST路径/请求结构/鉴权/Origin/404隐藏归属不变，不新增普通故障或渠道关闭HTTP。库存确认/待履约归.5、退款执行归B-05。

### 13.2 实施中发现并修正

首轮HTTP暴露IOrderLifecycleRepository同时匹配仓储/服务的依赖歧义，改经明确的IOrderLifecycleService查询取消准入并委托仓储。真实SQL校验发现V8 ck_close_frozen要求close_reason和A请求同时存在；本轮将早期reason冻结在渠道请求中，取得证明后再连同A请求一次写入，保留旧约束/迁移。初始旧关闭保护测试误把服务的拒绝受理快照当异常，按现有契约修正断言；HTTP仍按原逻辑返回409。上述失败批次保留target/payment-closing/b044-20261010-01～07，不作为最终通过证据，不清除其中资金/HELD样本。

验证入口新增docs/tests/run-b04-payment-closing.ps1（独立SQL/HTTP及新JVM）和run-b03-readiness.ps1 -WithPaymentClosing（真实A，隐含TradeRecovery/LocalOrders，与WithPayments/WithSettlement/旧关闭/联合故障互斥，必须全新批次）。异常注入仅verification；普通包无verification/Flyway。最终通过结果及当前状态在本节后续记录。

### 13.3 最终验收、证据与边界

B-04.4已完成。总报告target/payment-closing/b044-20261010-delivery/report.json；最终普通app SHA256 `2901AA3850D82F8ADE77C8ED18D5D4C1E53EEE23D6C843092B81C4AF884D8E5F`，verification SHA256 `5F0506CA38B8D5E350AB4865890461CF1915AF0143CA9AD8D10710F60E9E5C7E`。前端package-lock保持原SHA256 `4D0959125BAE132BEDBE0300916CBCDDA852FBF95D97E39C42FF38B13174861F`，无依赖升级。复杂度高，按停止支付/租约互斥→独立根裁决→原证明/声明冻结→A关闭/query→原子释放→回归/文档六步收口。

| 验收 | 通过证据与实际范围 |
| --- | --- |
| 构建 | target/b044-build-final.log：七模块、73项JUnit，0失败/错误/跳过；新增5项完整根证明领域检查；target/b044-frontend-final.log：vue-tsc/Vite通过 |
| SQL/HTTP竞争 | target/payment-closing/b044-20261010-final/verify.txt：真实MySQL与本人HTTP，根不存在/迟到create/迟到成功/旧支付令牌、第5次UNKNOWN告警仍恢复且无A close/无释放、已付未M2胜出/原Outbox/无伪退款、8笔新订单的并行根裁决、全FAILED＋待发重试覆盖、释放流水后注入故障的完整回滚、A离线原verifiedAt/hash、实际到期新A查询、旧NEVER_OPENED永久阻止开放、矛盾证明原文quarantine、旧A查询令牌失效 |
| 新JVM | 同批recover.txt：独立渠道关闭提交后响应丢失，第二JVM/checkout关闭，查询原根/closeId、首次冻结原证明与A请求；A query CANCELLED后只有一笔RELEASE。原checkout/关闭恢复相互独立 |
| 真实A | target/b03-readiness/b044-20261010-live-final/payment-closing.json及txt：真实Java8 A、TLS签名query、渠道开放/完整关闭证明、A CLOSED_UNPAID close、仍CLOSING/HELD，随后完整CANCELLED query、原hash保持、一笔RELEASE及该订单guard清除。真实装配开启资金/关闭接续，未用verification A替代；report.json记录进程/端口/环境收尾 |
| 原支付/资金回归 | target/payments/b044-payments-regression/verify.txt及recover.txt；target/settlement/b044-settlement-regression/verify.txt及recover.txt。本人HTTP/原键/锁等待/资金与Outbox原子性/签名/严格A结果/D6持久工作/新JVM恢复继续通过；回归后仅进一步加强.4关闭原裁决与当前根/尝试一致性及请求归属核对，最终SQL/新JVM/真实A已覆盖最终包 |
| 下单/旧关闭回归 | 本最终目录orders.txt、closes.txt，及target/b044-orders-regression.log、b044-closes-regression.log。原close marker、未发D27、关闭丢响应、锁等待、同事务回滚、原请求hash/verifiedAt、权限/所属/原订单幂等保持。正文V7/V9/21为旧探针范围标签，当前库版本/权限以迁移报告为准 |
| 双库迁移/权限 | 同最终目录development-migrations.txt、development-permissions.txt、test-migrations.txt、test-permissions.txt：双库当前V12/13份历史迁移，最终migrationsExecuted=0；开发库首次V12见live-01/database.credentials.xml-migrate.txt，隔离首次见b044-20261010-01/migrate.txt。runtime34表DML、DDL/history/A/system/grant拒绝；无清库/改A |
| 契约/交付 | 同最终目录contract-validation.json：6操作/23 schema/123引用、11正例/46反例；7份原支付HTTP与3份实际订单GET/取消响应（开放、CLOSING、CLOSED）通过。B-03 OrderResponse在内存按B-04增量扩展，schema子集校验，不称完整OpenAPI验证。B-02/B-03/A契约、旧迁移/历史SHA保留；delivery-audit.json记录秘密/私钥/令牌及忽略文件审计 |

未新增B-04.4专用Edge页面矩阵；本轮只改取消准入与文字，真实HTTP和前端构建已核验，完整浏览器＋资金/团队联合故障仍归.6。既有.2/.3 Edge结果仅作各阶段历史证据，不冒充本轮新验收。真实readiness还包含直接A占位及另一笔B JOIN样本，不把本轮一个未付关闭当作全部团队资金闭环。

当前b-04/7cef241，全部改动未暂存/提交/合并/推送；原B主目录和A工作区保持干净，A契约不变。验收拥有的进程退出、端口释放、调用者环境及默认Java8恢复；共享中间件保持运行。普通支付/资金开关默认关闭，本轮不提前开放完整普通资金链路。

继续保持旧成功/UNKNOWN/异常样本及HELD/guard、原paidAt/原事件/核对义务；本轮故障证明样本仍留档并处于核对，不人工清除。下一阶段.5接TEAM_COMPLETED、库存CONFIRM与待履约；.6联合故障与总交接；B-05才执行核对/退款。D1～D7不变，无新增未答方案。

### 13.4 重复验证入口

必须指定B JDK21与全新RunName，不复用未知资金订单，不改系统默认Java8：

```powershell
./scripts/mvn.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -MavenArguments @('-B','package')
./docs/tests/run-b04-payment-closing.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <新的隔离关闭批次> -SkipBuild
./docs/tests/run-b03-readiness.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <新的真实关闭批次> -WithPaymentClosing -SkipBuild
./docs/tests/run-b04-payments.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <新的支付回归批次> -SkipBuild
./docs/tests/run-b04-settlement.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <新的资金回归批次> -SkipBuild
./docs/tests/run-b03-closes.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -SkipBuild
./docs/tests/run-b03-orders.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -SkipBuild
```

固定database/orders/closes报告串行执行并复制到独立证据目录；不把覆盖后的旧路径当作原批次。秘密继续只来自被忽略的DPAPI/密钥文件，普通启动不执行迁移。

## 14. B-04.5 成团、库存确认与待履约（已完成）

2026-10-10接续核对b-04/7cef241及当前代码：.0～.4全部未提交，保留既有源码/文档/异常样本。原TEAM_COMPLETED只有原Inbox/每订单WAITING_DEPENDENCY，尚无确认入口。D3/联合设计第6节及A契约为实施依据，无新增业务选择。

计划：V13新增单订单唯一PENDING待履约与35表精确DML授权；按业务锁序及原每订单工作租约，事务外补查原Trade.query完整支付，核验本地SUCCEEDED/A ACCEPTED/可信名单及版本；同事务HELD→CONFIRMED、reserved→sold、唯一CONFIRM、原guard清除、GROUP_COMPLETED/待履约。接入本人订单视图；验证早到、乱序、重复、并发、锁后租约、故障回滚/新JVM及实际A成团，维护过程与路线图。未知/拒绝/矛盾不履约；失败/核对继续B-05接管，普通开关不提前开放。
### 14.1 已落地的处理边界

- V13新增b_fulfillment，order_id主键确保一订单一条PENDING；保存冻结订单、成功资金摘要、原成团消息、最新名单、完整Trade.query及库存前后快照/hash。既有V1～V12（含V10.1）不改写；runtime精确35表DML，普通包不含迁移/verification。
- FulfillmentService按每订单工作领取30秒租约，事务外查询A完整支付；FulfillmentRepository按既有全业务锁序，锁后读取数据库时间并核对token/intent/lease。缺本地订单/资金/A接受持续WAITING_DEPENDENCY；查询失败指数退避，5次alerted后仍恢复，不把UNKNOWN/异常变为可履约。
- 同时核对原消息/hash、source/channel/team/activity/名单、最新团队游标/hash、单订单A资金全部字段及精确版本。本地必须SUCCEEDED且ACCEPTED、无review；旧消息不因较新COMPLETED游标丢弃，但过时A查询继续等待。矛盾原文进入quarantine并保留工作/库存。
- 每成员独立事务：HELD→CONFIRMED，reserved减1/sold加1，唯一CONFIRM，GROUP_COMPLETED、清除本单guard、PENDING及work DONE一起提交。任一写失败全部回滚；重复完成核验既有履约/流水，绝不再更新库存或后来订单的guard。TEAM_COMPLETED Inbox必须所有名单工作DONE才DONE，部分完成/缺成员仍等待。B-05失败/核对工作继续持久接管。
- 本人订单返回nullable fulfillmentSummary(status/confirmedAt/paymentId/teamId)，读取独立于checkout和MQ开关；页面待成团继续有限轮询，成团后显示库存确认/等待履约和时间。发货/退款不在本阶段。

### 14.2 验证进展与诊断

target/fulfillment/b045-20261010-final/verify.txt、recover.txt已通过：真实MySQL/独立渠道、成团早于商城资金/A接受、并发单租约、完整A支付字段、库存/流水之后注入待履约插入失败的事务回滚、完整事务回滚、过期令牌、新订单实际占用guard后旧完成重放、旧消息配较新游标/旧查询继续等待、5次失败告警仍领取、缺订单持久接收、新JVM/checkout关闭原工作恢复，恰一CONFIRM/PENDING。

早到样本先渠道成功后团队早于本地M2；不在已完成团队上创造新支付，保持原支付准入。初轮验证发现探针引用不存在的work.team_version、库存version及二进制JSON查询不匹配，已按现有表列/原证据修正，未修改旧迁移。真实A初轮b045-20261010-live-01/02的准入/时效探针未完成，保留FAILED报告及HELD样本；.02明确PAYMENT_TIME_UNVERIFIABLE，后续按原D7等待新占位安全时间并预热真实TLS查询。b045-20261010-live-final两笔资金均被A接受，但本批活动实际target=3，未收到完成事件；后续补齐三笔完整B订单，不改目标人数，不绕过时效限制、不清旧样本。既有Hessian/JDK21反射输出按历史观察，最终以业务断言为准。

消息回归首批b045-settlement-regression的recover未选到本批通知：历史未ACK样本超过旧探针100条领取窗口，资金/Outbox仍保持。已仅把本批拥有的READY通知next_attempt_ms置0后走原渠道租约/ACK，其他事实/通知不清除；通过批次另记为b045-settlement-regression-pass。页面初轮的刷新探针把正常登录续期POST误计为业务写入，已改为仅统计订单/支付/购买接口，保留失败日志和截图。后续完整三笔B订单的真实A、页面及受影响回归已通过，最终证据见14.3；失败批次保留，不作为通过证据。

### 14.3 最终验收与实际范围

| 验收 | 本轮证据 |
| --- | --- |
| 构建/领域 | target/b045-build-final.log：七模块、76项JUnit，0失败/错误/跳过；新增3项完整支付/资金接受/精确版本领域断言。target/b045-frontend-final.log及b045-browser-frontend-build.log：vue-tsc/Vite通过 |
| SQL/并发/恢复 | target/fulfillment/b045-20261010-final/verify.txt及recover.txt：14.2所列原子性/实际插入失败/并发/租约/新JVM，完整成功证据匹配；缺钱/A接受/缺订单不履约，连续失败保留工作 |
| 真实A完整团队 | target/b03-readiness/b045-20261010-live-pass/fulfillment.json、txt：本活动target=3，三笔B OPEN/JOIN订单、三个独立渠道成功/原支付事件、真实签名MQ接受回执及TEAM_COMPLETED名单；逐单TLS Trade.query完整支付核对后，三笔唯一CONFIRM/三条PENDING，原guard解除。available6/reserved1/sold3，另一团队的B JOIN仍HELD；未用直接A支付替代任一本团队成员 |
| 页面/本人隔离 | target/payments/b045-browser-20261010-pass/browser.json和三张截图：Edge桌面待成团→自动轮询成团/PENDING、390px无横向溢出、0页面错误、刷新0订单/支付/购买写；A接受/完成/完整查询由verification控制，非真实A浏览器。消息开关关闭仍读取本人PENDING。真实A批次另验证实际本人GET摘要及异主404，保存fulfillment-order-http.json |
| 受影响回归 | target/payments/b045-payments-regression、target/settlement/b045-settlement-regression-pass、target/payment-closing/b045-closing-regression的verify/recover：本人HTTP/原键/UNKNOWN/资金Outbox/签名结果/D6/已开放关闭竞争继续通过；旧下单/关闭见本交付目录orders.txt、closes.txt及target/b045-orders-regression.log、b045-closes-regression.log |
| 双库/权限 | 本交付目录development/test-migrations.txt、development/test-permissions.txt：当前V13/14份历史迁移，已执行迁移校验通过，runtime精确35表DML；DDL/history/A/system/grant拒绝。V1～V12不重写，既有业务数据不清除 |
| 契约/交付 | target/fulfillment/b045-20261010-delivery/contract-validation.json：原支付实际HTTP、原关闭样本及两份新的成团GET响应按B-04增量校验；旧B-03订单schema只在内存扩展，不改历史契约，purpose-built子集校验不称完整OpenAPI。delivery-audit.json记录源码秘密/私钥/令牌/忽略文件检查；report.json记录产物SHA与边界 |

真实A与页面批次使用补修旧消息通知探针前的同业务源码包；最后仅修改verification中本批通知的领取排序以避开积累样本的100条窗口，普通业务源码未变。最终构建及消息/关闭/下单回归使用下列最终指纹，历史批次不冒充同一二进制。

最终产物指纹（本批，旧历史SHA保持）：

- zj-market-app/target/zj-market-app-exec.jar：`A021F85F285BFED89266B3E1A0351DF1949957B3DBD4893D99E00AAB3DC42FCF`
- zj-market-verification/target/zj-market-verification.jar：`E64AEE21882DD944F47B8A1502DC129BF089B1DBEF0508C11480A185DC4A0ABA`
- frontend/package-lock.json：`4D0959125BAE132BEDBE0300916CBCDDA852FBF95D97E39C42FF38B13174861F`
- zj-market-infrastructure/src/main/resources/db/migration/V13__group_completion_and_fulfillment.sql：`AE8229B349DB7C6A9BFF17D2F636110DE5D8266C079617C443049D3F6974CA2E`

当前b-04/7cef241，.0～.5全部成果未暂存/提交/合并/推送；主B与A工作区保持干净、A契约不变。自有进程/端口退出，环境及默认Java8恢复，共享中间件保持运行。普通checkout/events仍默认关闭；旧成功、UNKNOWN、矛盾/退款义务、失败批次及后来新订单HELD/guard全部保留，不人工抹除。

### 14.4 接续与重复验证

B-04.5只确认可信成功团队的库存并建立PENDING，没有发货/物流/退款执行。B-04.6继续全链路联合故障、完整矩阵/交接，普通成功链路总验收仍待.6；B-05执行已持久接管的核对/退款。D1～D7不变，无新增未答方案，不自动开始.6。

指定JDK21及全新RunName，串行执行含provision/固定报告的探针：

```powershell
./scripts/mvn.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -MavenArguments @('-B','package')
./docs/tests/run-b04-fulfillment.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <新的隔离成团批次> -SkipBuild
./docs/tests/run-b04-fulfillment-browser.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <新的页面批次> -SkipBuild
./docs/tests/run-b03-readiness.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <新的真实三人成团批次> -WithFulfillment -SkipBuild
```

先用现有provision入口升级双库并确认35表授权；普通启动不运行迁移。WithFulfillment必须新批次，与其他资金/关闭故障开关互斥，复用真实A已有TLS/ACL消费者配置；不改A契约/源码、不拿旧超时/未知订单硬凑新团队。真实新占位需满足原D7安全窗口，TLS预热仅在verification探针，不放宽普通准入。

## 15. B-04.6 联合故障验收与B-05交接（已完成）

2026-10-10核对实际b-04/7cef241，.0～.5全部未提交成果保持，主B/A不改。按20.3与联合设计矩阵开展新批次，不直接复用旧报告作本轮通过依据。

计划：建立串行总验收入口及同包指纹/报告留存；新批次运行独立渠道/MySQL/跨JVM、真实A/MQ三人成团与已开放关闭、真实A停启旧关闭恢复、浏览器及受影响下单/关闭回归；只读审计持久核对/退款工作和库存边界；建立B-05接续入口、剩余设计/验收条件并同步路线图。普通资金写仍默认关闭，退款/核对执行不在.6实现。

代码检查发现SettlementJob将资金与履约放在同一try内，资金扫描异常会跳过履约。本轮拆分异常处理；以真实调度线程连续两轮故障验证订阅、资金、履约异常不终止后续扫描，保持原证据/锁序/事务。未修改旧迁移或A契约。

### 15.1 验收进展及保留的失败

首轮b046-20261010-01总验收通过：77项JUnit、四类独立SQL/新JVM、B-03下单/关闭/联合故障、真实A三人成团/资金/开放后关闭/停启旧关闭、两类Edge及D6只读接管审计。该轮不含随后新增的真实期限流逝后才首次M2观察场景，不作为最终包的全量结论。

补充探针仅verification的短A窗口：渠道在冻结期限内成功并独立提交，实际等待数据库期限经过后，A离线情况下首次observe，核对原paidAt/一份Outbox/无伪退款或库存动作。b046-20261010-final在该断言失败：两个Long时间使用对象身份比较；修正为Objects.equals值比较，业务资金代码未因此改动。失败报告及HELD/原成功事实保留，环境/端口/默认Java8/主B与A收尾通过。另起b046-20261010-final-pass完整重跑，不覆盖失败报告。

总入口新增自包含标准库validate-b04-contracts.py，校验6项HTTP增量/真实响应/历史契约与迁移/文档链接和SHA/普通包边界及双库35表权限报告；明确只是Schema子集，不称完整OpenAPI符合性。交接见[b04-b05-handoff.md](b04-b05-handoff.md)。

### 15.2 最终联合验收与证据范围

最终独立批次target/b04-acceptance/b046-20261010-final-pass/report.json为PASSED；77项JUnit、七模块/前端构建，以下业务探针全部采用本批开始时冻结的相同JAR，结束再次逐项核对指纹。b046-20261010-01首轮通过及b046-20261010-final失败均保留，不冒充最终包证据。

| 范围 | 最终证据（总目录保存通过摘要与SHA，原目录保存详细日志/样本） |
| --- | --- |
| 调度与普通包 | build.log：77项0失败/错误/跳过；新增真实线程两轮订阅/资金/履约异常仍扫描；normal-runtime.log为JDK21普通入口，普通包无verification/Flyway |
| 模拟支付/本人HTTP | payments-verify.txt/recover.txt，原目录target/payments/b046-20261010-final-pass-payments：原键/响应丢失/失败重试/成功唯一/权限/开关/锁后时效/独立渠道及新JVM，UNKNOWN与HELD保留 |
| 可信资金与可靠通知 | settlement-verify.txt/recover.txt，原目录target/settlement/b046-20261010-final-pass-settlement：M2与原Outbox原子回滚/并发幂等/签名与同事件异正文隔离/严格A资金匹配/缺订单D6/唯一退款义务/新JVM丢ACK恢复。新增真实数据库期限流逝后才首次observe期限内成功，A离线仍保存原paidAt/一份事件，无误退款/释放/履约 |
| 已开放关闭与竞争 | payment-closing-verify.txt/recover.txt，原目录target/payment-closing/b046-20261010-final-pass-payment-closing：全尝试根证明/成功关闭单裁决/UNKNOWN不A未付关闭或释放/迟到操作受阻/锁后fence/释放事务故障/旧NEVER_OPENED不改写/新JVM原closeId及唯一RELEASE |
| 成团与确认 | fulfillment-verify.txt/recover.txt，原目录target/fulfillment/b046-20261010-final-pass-fulfillment：早到/乱序/依赖/并发/过期租约/完整支付与名单/流水后插入失败回滚/连续告警仍恢复/新JVM一次CONFIRM/PENDING，重复不清后来guard |
| 真实A三人成功 | real-a-fulfillment-*，原目录target/b03-readiness/b046-20261010-final-pass-live-fulfillment：实际Java8 A、TLS/MQ签名链路、三笔完整B OPEN/JOIN独立渠道付款与完整名单/Trade.query，3 CONFIRM/3 PENDING；available6/reserved1/sold3，另一团队仍HELD；本人实际HTTP与异主404 |
| 真实资金/关闭 | real-a-settlement-*、real-a-payment-closing-*：真实MQ结果及原eventId/完整Trade.query补查、Broker ACK不作A接受；实际开放后根关闭证明→A CLOSED_UNPAID→权威CANCELLED→一次RELEASE，原证明/hash保持 |
| A停启与受影响B-03 | real-a-joint-faults-*、b03-orders.txt/closes.txt/joint-faults.json：实际A旧未付关闭路径离线不释放，新A PID/新B JVM恢复原请求；库存并发/守恒/取消迟到竞争回归。此停启场景为旧NEVER_OPENED，不称真实已付退款演练 |
| Edge前端 | payments-browser.json、fulfillment-browser.json，原目录target/payments/b046-20261010-final-pass-payments-browser及-fulfillment-browser：真实B页面/独立模拟渠道，A由verification受控；丢响应/404先查原键/双标签与账号隔离/失败重试/刷新不写/桌面和390px，待成团轮询至PENDING。真实A同轮另以实际本人HTTP验证结果；未把受控浏览器冒充真实A浏览器同一会话 |
| D6及安全交接 | handoff-snapshot.json：累计隔离库六项违规均0——多成功、成功/UNKNOWN被释放、履约缺确认、成团缺PENDING、待退款丢HELD/guard、work证据hash不符；仍保存缺本地/DEFERRED_B05/异常及过期工作。统计含历次受控/真实A样本，不是生产待退款数量 |
| 迁移/权限/契约/交付 | development/test-migrate.txt与permissions.txt：双库V13、14份成功历史迁移，本批执行0、精确35表runtime DML，DDL/history/A/system/grant拒绝；V1～V13含V10.1不改写。contract-validation.json为6操作/24 schema/127引用、11正例/46反例及4项履约反例、7份支付及5份订单响应，Schema子集校验；delivery-audit.json检查源码/密钥令牌/忽略边界 |

各真实A批次的provenance.txt记录独立A/B JDK、A包及契约SHA、B包SHA，完整原事件/查询证据保留。业务网络调用仍在商城事务外，普通商城未新增故障HTTP、退款或强制成功/释放入口。当前模拟资金成功链路与未付取消安全门槛按B-04范围已通过，不证明第三方资金安全或完整失败退款闭环。

### 15.3 指纹、收尾与B-05接续

最终同包指纹（历史指纹保持）：

- zj-market-app/target/zj-market-app-exec.jar：`5BA9DFC5F9FA13EB12347F957D743FE06D1D72698F44009CA878C50FCD875BE8`
- zj-market-verification/target/zj-market-verification.jar：`D9AE24D9378EE2C456C92F09A98B681C7E46BB664AAA430D7F552FFDB9405872`
- frontend/package-lock.json：`4D0959125BAE132BEDBE0300916CBCDDA852FBF95D97E39C42FF38B13174861F`
- ../group-buy-market/docs/ab-api-contract.md：`83B02A7EBF5E80B5EF4D1B03936E6B1CA33EED32F6D9C68B451E855C6192D7DD`

当前b-04/7cef241，B-04.0～.6按上述模拟范围完成；全部改动未暂存/提交/合并/推送。A契约/主A及主B保持，报告确认调用者环境恢复、默认Java8不变、自有端口释放；共享MySQL/Redis/RocketMQ未停止。普通payment/checkout/events默认关闭，需显式隔离配置启用；本轮不自动开放普通环境。

B-05以[b04-b05-handoff.md](b04-b05-handoff.md)为入口，接续完整到期名单核对、稳定refundId及渠道退款尝试、可信全额退款/原事件和A结果、失败/UNKNOWN恢复、唯一释放与guard收尾及最小运营能力。原成功/UNKNOWN/异常/失败样本和工作原文继续保留，不能凭超时/Inbox DONE或DEFERRED_B05解除HELD。D1～D7不再询问；稳定refundId已由A契约固定，新退款尝试/故障及运营策略在B-05逐项确认。B-05/B-06尚未开发，不伪报退款或发货完成。

本阶段未停Broker/Redis做带资金故障、未做跨主机/生产TLS、多实例或真实第三方退款；这些与B-05失败全链路、B-06实际部署总联调分别接续。浏览器和真实A证据来源如15.2所列，不能声称所有页面操作均在同一真实A会话完成。

### 15.4 可重复入口

指定已安装JDK21/Python3与新的RunName，串行运行，入口拒绝覆盖旧批次/占用无关端口，固定报告在下一步前复制并校验SHA：

```powershell
./docs/tests/run-b04-acceptance.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -PythonExecutable 'C:/Program Files/Python313/python.exe' -RunName <新的联合批次>
./docs/tests/run-b04-handoff.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <新的只读交接批次> -SkipBuild
```

总入口依次构建/普通启动→双库provision→四类资金SQL/新JVM→受影响B-03→四类真实A新批次→两类Edge→只读交接→自包含契约检查→交付审计，并核对同包、端口/环境/主目录。只读入口不推进业务，但外层provision会验证既有迁移/授权；不要把它当生产只读连接工具。最终文档更新后补跑契约/交付审计并刷新报告相应摘要SHA，业务证据与包不重写。

## 16. 模拟通知写回租约补修（已完成）

2026-10-10用户评审P2确认：SimulatedChannel.retry/acknowledge在UPDATE取行锁前读DB时间，锁等待跨租约且token未换时旧处理者仍可写回。当前b-04/7cef241及全部未提交成果保留；不能据此断言重复库存扣减，亦不改写第15节历史验收报告。

计划：先SELECT通知行FOR UPDATE，再独立语句取DB时间并核对LEASED/token/lease；保留最终UPDATE条件防御。verification用真实MySQL连接持行锁，观察另一线程真实JDBC语句进入且租约仍有效，阻塞到数据库期限经过后释放，验证ACK、REVIEW ACK和retry均无写；真实领取替换token后验证旧令牌无效及新令牌有效。仅本批通知设置/恢复测试租约，不修改渠道成功或资金/库存事实。构建/受影响资金及库存确认回归后更新本节与路线图，普通开关/迁移/A契约保持。

### 16.1 实现与专项验收

retry和acknowledge共用noticeTime：在各自独立事务内先SELECT FOR UPDATE通知行，再以独立SELECT取数据库时间，核对LEASED、相同token及未过期lease；不满足即无写，保留UPDATE条件。未新增迁移/HTTP/故障入口或改变A契约，普通payment/checkout/events默认false。

新增verification/NotificationLeaseRegression并接入SettlementCommands及既有run-b04-settlement.ps1。真实MySQL独立连接持通知行锁，另一线程在租约有效时进入JDBC，确认实际阻塞，等待DB时间跨期限后释放锁；普通ACK、REVIEW ACK、retry三组均不改变状态/token/期限/重试时间/次数/hash。另三组通过真实notices领取替换token，旧token写回无效，新token ACK/重试有效，终态重复调用无效。仅设置并恢复本批自有通知，渠道成功、商城资金与库存事实不改写。

本轮JDK21构建通过，77项JUnit零失败/错误/跳过；新增六组是实际SQL验收，不计入JUnit数量。专项资金批次target/settlement/b04-notice-lease-20261010-02通过新六组及原资金/Outbox/签名/D6/期限事实/新JVM丢ACK恢复；支付批次target/payments/b04-notice-lease-20261010-payments、库存确认批次target/fulfillment/b04-notice-lease-20261010-fulfillment均verify/recover通过。库存探针验证新JVM唯一CONFIRM/PENDING，不能反推原缺陷已导致重复扣库存。

首次target/settlement/b04-notice-lease-20261010-01在Docker引擎未运行时准备数据库失败，业务回归尚未执行；已保留失败目录，恢复已有Docker Desktop后另起02通过，未清除历史样本。补修独立报告target/b04-notice-lease/20261010-pass/report.json及摘要保留。此次为受影响范围回归，未重跑真实A/MQ/浏览器全矩阵；第15节原历史批次与指纹不改写、不冒充新包全量证据。

补修包指纹：

- zj-market-app/target/zj-market-app-exec.jar：`BF213BB1F6EADCF89CCF3D36E49D59F606CEFC9341DFD15F20CD70DA317EC67C`

- zj-market-verification/target/zj-market-verification.jar：`8A2E9B1791F506550F5A0109F71ED879744F56423CF5EE16D6A7ED09642FC66D`

主B/A仍干净；b-04全部成果仍未提交/合并/推送。共享中间件保持运行，B-05/B-06未开展。

## 17. B-04提交、主分支集成与发布记录

2026-10-10用户明确授权提交当前工作树到b-04、合并master并上传远程。操作前核对b-04/master及新获取的origin/master均为7cef241，远端无b-04，主B工作树干净。提交前交付审计383文件、126项已知密钥检查无命中，忽略边界及差异空白检查通过；沿用第15/16节已完成的验收，不把提交操作当新业务验收。

全部非忽略源码、前端、迁移、工具与文档提交为1b5242ed1d34722dba52b84a3962e6dc3abb41b2（feat: complete B-04 simulated payments, settlement and fulfillment）。在D:/Java/zj-market的master以ff-only合并，无冲突；原子推送origin的b-04/master成功，两远端引用核验同为该提交，b-04建立上游。凭据、构建包、数据库和完整运行证据继续留在忽略的.local/target，不纳入远端；本地样本不清理。

随后以单独文档提交记录本次真实Git状态，沿同样快进及原子推送同步两分支。历史开发记录、失败批次和SHA不改写；远程仓库https://github.com/zjing-259/zj-market-B.git。主A不修改，普通资金写默认关闭，B-05/B-06不由本次发布自动开展。
