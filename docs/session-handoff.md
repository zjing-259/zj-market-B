# 本会话恢复入口

更新：2026-10-08。用途：上下文压缩后的最小恢复信息，不替代项目契约和阶段文档，不覆盖A任务进度。

## 当前任务与状态

- 当前任务：B-02.3商品主数据与版本。代码在D:/Java/zj-market-b01（codex/b-01），原目录维护唯一[B-02过程文档](D:/Java/zj-market/docs/b02-development.md)及[HTTP契约](D:/Java/zj-market/docs/b02-http-api.json)。.1/.2已完成；.3已完成实际验收，**D12用户选择沿用A的128个UTF-16单元上限，边界与完整回归通过**；.4～.6未开展。
- D1～D9既有选择继续有效：开放普通注册、RS256 JWT+轮换、Vue3/TS6.0.3/Vite、简易管理/HTTPS图片、MyBatis显式事务、统一商品版本、Argon2id、单实例进程限流。新增D10用户选择名称去首尾空白/描述保留原文；D11检测HTML标签直接拒绝而不自动清洗。
- D12用户已确认B沿用A的128个UTF-16单元上限；后端strip/trim后String.length、前端长度校验/上限提示已落实。128普通中文/64emoji/混合128单元创建和编辑成功；129/130单元拒绝且无版本/事件变化；合法名称数据库及冻结A快照完整保留。OpenAPI通过x-max-utf16-units=128及description补充标准maxLength的计数语义。A未改；没有未回答的.3选项。

- .3新增domain Product/Fields(BigDecimal)、ProductSyncProgress，application ProductService/ProductStore事务仓储端口/ProductEventPort，infra MyBatisProductStore/ProductMapper/ContractProductEvents/ProductConfiguration。商品+9字段信封/6字段A完整快照+当前同步目标同一事务，冻结UUID/版本/UTC毫秒/关联requestId。SELECT FOR UPDATE后expectedVersion/CAS，无变化不增版，有效图片/描述编辑也增版，溢出409 PRODUCT_VERSION_EXHAUSTED。未发送MQ、未消费A结果、未实现试算。
- 6商品HTTP：公开GET列表/详情、运营GET列表/详情和POST/PUT。严格money/version字符串、完整PUT/unknown字段拒绝；运营handler和原访问filter双重检查当前Principal，实际编码路径权限回归通过。/admin/users/me补handler角色检查。前端Products.vue接入公开浏览、运营维护、图片失败占位、冲突显式重读/写请求只发送一次，保留身份页面。
- V3__product_authority.sql新增b_product/b_product_outbox/b_product_sync，开发zj_market和独立zj_market_b02_test均显式迁移，runtime只8张B表DML（探针+4身份+3商品），拒绝Flyway历史/DDL/A/system/grant；V1/V2未改。测试自有随机样本保留，不清A或开发业务数据。
- 商品配置B_PRODUCT_ENABLED默认false，事件producer/source/channel外部注入；scripts/start-products.ps1复用身份/JDK21/DB入口；start-identity.ps1仍仅身份。scripts/products.ps1只接受精确B测试库scope/account；docs/tests/run-b02-products.ps1和run-b02-products-browser.ps1为复现入口。身份/数据库维护CLI显式关闭商品模块避免继承无关配置。
- 最终15项Maven、实际商品HTTP/MySQL（并发、历史body、三事实回滚、断库）、身份HTTP/浏览器回归、商品Edge浏览器、正式TS6类型/Vite构建均通过。证据target/b023-products-final.txt、target/products/verify.txt、browser.txt、store.png、operator.png、target/b023-browser-final.txt、target/products/environment-restore.txt。环境全部恢复/18092和5173释放/终端Java1.8.0_391/普通包无Flyway或验收程序已确认。D12最终证据target/b023-d12-http.txt、target/b023-d12-browser.txt、target/products/d12-environment-restore.txt，最终Maven15项、实际HTTP/浏览器、前端类型及生产构建、全部环境恢复/端口释放/终端Java8保持通过；.3已收口。
- 开发V3与权限证据target/products/development-migrate.txt、development-permissions.txt；测试target/database/*.txt。最新一键验收未改变A；RPC/MQ/签名仍引用先前已通过target/environment-probe/b022-20261008，不机械重复发送。
- JDK21/Boot4.1.1/Netty4.1.118.Final、独立签名Jackson2及HTTP Jackson3保持；原目录源码/POM未同步，工作树改动未提交/合并。没有改A源码或清A数据；已有容器保持运行，临时B/Vite进程已结束。
- 不自动开展.4；用户要求方案选择交用户、B-02及以后各阶段单独过程文档（B-01不补建），任务文档末尾复杂度，高复杂度列目标/依赖/验收。.3为高，四步及已完成D12见过程文档第12节，D12收口本身复杂度低。

## 按需读取的权威资料

1. [B开发路线图](development-roadmap.md)：当前主任务目标、DDD边界、阶段及验收。
   [B-02开发过程](b02-development.md)和[HTTP契约](b02-http-api.json)：本阶段具体设计、选择、进度和验收记录。
2. [B业务词汇](../CONTEXT.md)：术语；不要写入部署和实现细节。
3. [A/B契约](../../group-buy-market/docs/ab-api-contract.md)：当前Dubbo3/Triple＋RocketMQ协议、业务规则及Schema引用，B不要另建冲突副本。
4. [A交付报告](../../group-buy-market/docs/phase5-ab-v2.md)、[A进度](../../group-buy-market/TASK_PROGRESS.md)：兼容矩阵、已有验证及环境恢复；涉及实际接入时再读。
5. [A维护清单](../../group-buy-market/A-TODU.md)：历史问题和未关闭验收，不重复实施已修复项。

## 必须保留的会话约束与增量结论

- 用户临时规则**仅本会话生效**：每次新建/修改任务文档，文档末尾写明此次任务实施复杂度及依据；复杂度高须拆成小阶段，注明目标、依赖和验收。不要将此偏好自动升级为其他会话规则。
- 已判断A达到供B接入开发的阶段性交付标准。实际B/跨主机/生产故障验收尚未完成，不阻塞B开始开发，但不是整个系统可上线。
- 当前Schema已进一步收尾为216个非法变体；本会话最后独立离线检查通过七类样例、九结果分支、216非法变体、两个契约示例和生成一致性。17条真实Outbox在前一轮146非法变体验证时独立只读复验通过；不要称本会话最后一次离线检查重新读了数据库。
- 保留现有未提交修改；不擅自提交、回退、清洗数据或重复执行迁移。A旧65项、v2专项、实际传输证据及边界按A文档引用，避免无新改动时机械重跑。
- 工作环境为Windows/PowerShell；会话cwd可能仍在A，操作B时显式指定 `D:/Java/zj-market`。未输出或持久复制本地凭据。
- 本轮检查未发现可由助手调用的原生上下文压缩工具；本文件只负责持久化接续，不能据此声称客户端历史已被压缩。

## 本次更新的复杂度评估

复杂度：低。本次仅保存恢复入口、文档引用及尚未落盘的会话约束，没有新增实现决策或业务变更。B整体开发复杂度高，六阶段及其细分已在路线图末尾记录，恢复时直接使用，不另起重复计划。

## B-02.1此次接续复杂度

2026-10-08：恢复记录维护复杂度低，更新已确认选择、HTTP设计结构检查和唯一过程文档入口。实际B-02.1设计复杂度中等；D6已确认为RS256，不把设计成文等同功能实现，后续按六小阶段推进。

## B-02.1定稿记录与此次复杂度

2026-10-08：用户确认RS256后，B-02.1设计确认完成；过程文档记录范围、User/Product模型、JWT注册/刷新/撤销、Vue前端、MyBatis事务、15个HTTP操作及后续验收。后续按阶段维护各自文档，B-01不补建。此次恢复记录复杂度低，设计复杂度中等；没有实现接口或业务迁移，不自动进入.2。

## B-02.2此次接续记录复杂度

低：保存已授权实现、真实验收、隔离账号与唯一待选D9，避免把兼容探针当项目正式构建。B-02.2实际实现高复杂度，已按过程文档四步推进；待用户回答后完成前端构建收口，未提交代码或开启.3。

## B-02.2最终收口与此次复杂度

2026-10-08：D9由用户选择TypeScript6.0.3，已更新精确版本及锁文件，正式类型/生产构建、一键HTTP/浏览器验收和环境恢复全部通过，临时端口释放。B-02.2已完成，未提交或合并工作树、未开展.3。本次收口复杂度低；.2整体高复杂度及四步证据见唯一过程文档。

## B-02.4最终恢复入口与此次复杂度（2026-10-08）

B-02.4已完成，最新路线图和唯一过程文档以D:/Java/zj-market/docs/development-roadmap.md及b02-development.md第13节为准，不使用本工作树旧路线图的状态推断后续进度。源码/脚本在此工作树：start-sync.ps1启动正式同步；run-b02-sync.ps1 -Browser复现联调及页面；sync.ps1受控隔离维护。业务最多重新消费8次，独立组1次重试实际死信/RPC恢复通过。

最终15项Maven/打包、真实A/B故障矩阵、维护CLI及同步页面通过；身份/商品回归通过，开发/测试V4和11表最小DML通过。实际证据target/b024-package.txt、target/sync/b024-20261008-195839/verify.txt、target/b024-final-core.txt、target/b024-final-browser.txt和target/sync/browser.txt。默认Java8与环境恢复保持。B-02.5/.6尚未开展，未提交、合并或清洗数据；不要重跑忽略target代码生成器覆盖后续修正。

此次索引复杂度低，实际同步任务复杂度高，四步依赖及验收见唯一过程文档末尾。


## B-02.5接续索引（2026-10-08）

B-02.5已完成实际A试算、正常商城及在线/离线Edge验收；D17/D18已落实，受影响同步与身份/商品回归及环境恢复通过。完整记录唯一在D:/Java/zj-market/docs/b02-development.md第14节，最新状态见同目录development-roadmap.md及session-handoff.md；本工作树只保留索引，不另建B-02过程文档。完整入口scripts/start-market.ps1，B-02.6未开展，未提交或合并。

此次索引复杂度低；实际.5复杂度高，按权威文档四步完成。


## B-02.6最终交接（2026-10-08）

B-02.6及B-02整体闭环已完成。实际联合批次b026-20261008-220506、入口docs/tests/run-b02-acceptance.ps1、总报告target/acceptance/b026-20261008-220506/report.json为PASSED；15项测试/固定JDK21构建、双B库V4与最小权限/跨库拒绝、真实核心及在线/离线Edge、原签名/ACL基线通过。新增ACK窗口只在独立验收包：真实A结果落库后halt(86)，新B进程重收相同回执且Inbox一条/确认状态不变；业务8次重试保持。正常包不包含验收/Flyway，产物SHA256、环境全恢复/端口释放/默认Java8均存证。

唯一过程文档D:/Java/zj-market/docs/b02-development.md第15节：统一命令/矩阵、第15.2节B-01技术前置及遗留、第15.3节B-03字段输入及价格不保留语义；路线图已按证据更新。源码仍D:/Java/zj-market-b01、codex/b-01未提交工作树，不合并/清洗或覆盖旧改动。B-03尚未开展，实际开始时另建唯一B-03过程文档，后续方案取舍继续交用户。生产部署、正式TLS、备份、监控及压测目标明确留待后续，不宣称已上线。

此次联合验收与交接复杂度中等，三步均通过；B-02总体实现高复杂度。本工作树仅保留接续索引，不另建B-02过程文档。
