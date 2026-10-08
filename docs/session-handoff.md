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

## B-02.4 当前接续记录（2026-10-08）

用户已授权可靠同步开发，当前进行中，不能标记完成。D13～D16最终决策见唯一过程文档第13节：生产退避1/2/4/8分钟、5次告警后继续，运营暂停恢复，毒消息持久隔离，业务消费最多重新消费8次；学习验收独立组/库加速。

实际源码仍在D:/Java/zj-market-b01。V4已仅应用B测试库（11表），开发库尚待最终迁移。六模块构建及15项测试通过；新增SyncCommands/SyncDeadLetter及docs/tests/run-b02-sync.ps1正在联调，target/sync保存各次忽略证据。实际A离线持久保存、Broker确认不等于业务确认、重启RPC补查、发送后未落库的原事件恢复已通过；其余真实MQ、死信、运营HTTP/页面、回归和文档尚待最终收口。前端已加入同步状态、暂停/恢复、只读隔离查询，固定TypeScript6.0.3构建通过。未提交、清理或开展.5。

此次任务复杂度高，依赖与四步验收见b02-development.md第13～14节。继续期间不要重跑忽略target中的代码生成器覆盖后续修正。


## B-02.4最终接续与此次复杂度（2026-10-08）

B-02.4已完成，覆盖前述WIP状态。真实核心故障矩阵target/sync/b024-20261008-195839/verify.txt与b024-final-core.txt、最终15项Maven/六模块打包b024-package.txt、修正后真实同步页面b024-final-browser.txt及target/sync/browser.txt均通过；身份/商品原回归、独立维护CLI、双B数据库V4及11表最小权限通过。D13～D16无未回答选择，固定业务8次重新消费；独立组1次重试实测死信并真实RPC恢复，未进行业务9次消费。

实际源码仍D:/Java/zj-market-b01，统一启动start-sync.ps1；身份/商品单独入口显式关闭同步及RPC/MQ。脚本外部凭据、JDK21及普通包边界保持，A仍JDK8和隔离测试库；默认Java8、环境恢复与自有临时端口释放已确认。开发过程及18个HTTP操作（17实现）唯一在原目录docs/b02-development.md、b02-http-api.json，路线图.4已完成；.5～.6未开展，未提交/合并/清洗数据。target忽略目录代码生成脚本不要重跑覆盖当前修正。

此次恢复记录复杂度低；实际可靠同步高复杂度，四步依赖/验收已完成，边界与证据见唯一过程文档第13～14节。下一步须按用户后续指令开展B-02.5，继续将方案选择交用户。

## B-02.5接续（2026-10-08，实施中）

用户已授权.5，D17选择登录进入详情自动试算及手动重新试算，D18选择3秒读取B资料、最多1分钟后手动刷新。实际源码仍在zj-market-b01；新增MarketingTrialPort/Service、DubboMarketingTrial、受保护空正文HTTP、start-market.ps1及正常商城页面。固定JDK/Boot/Netty/签名和TypeScript版本均保持。普通身份/商品/同步入口显式关闭试算，正常B清除新增验收账号环境变量；实际A临时启动后恢复全部环境，不将A数据库凭据传给B。

.5构建15项测试通过；正在运行docs/tests/run-b02-trial.ps1 -SkipBuild -Browser，忽略target/trial目录存证。本轮A隔离样本须使用数值折扣ID，并同时创建自有crowd_tags主记录和成员明细。脚本复用已有独立A测试库，不改A源码、框架或开发数据，不自动升级A结构。正常B浏览器验收覆盖延迟真实报价并发编辑和实际一分钟刷新上限。不能根据前次失败或历史证据标记.5完成；继续检查最新运行日志，修正受影响入口再收口。

此次复杂度高，第14节四步依赖与验收仍推进中；B-02.6未开展，不提交或合并。不要重跑target里的代码生成器覆盖后来修正。

## B-02.5最终接续与此次复杂度（2026-10-08）

B-02.5已完成，覆盖前述WIP状态。实际核心及正常在线/离线Edge证据在target/trial/b025-20261008-214435，最终核心在b025-20261008-214819；15项Maven/六模块打包、原可靠同步实际故障回归b024-20261008-214923及原身份/商品HTTP和浏览器回归通过。默认Java8、全环境恢复、自有端口释放、正常包无verification/Flyway均确认。D17自动试算/手动重算、D18每3秒只读B最多1分钟后手动刷新已落实，无未回答.5选择。

实际源码仍D:/Java/zj-market-b01，完整入口scripts/start-market.ps1；.2/.3/.4单独入口显式关闭试算。当前HTTP契约18个操作全部实现、316本地引用有效。唯一B-02过程文档在原目录第14节记录真实A/受控输入的区别、配置、命令和证据。未新增V5或订单/库存/支付表，不缓存/保留试算价格。未提交/合并/清洗A数据；B-02.6尚未开展，不自动开始，后续方案选择继续交用户。

此次.5复杂度高，四步依赖及验收已完成；文档收口复杂度低。不要重跑target中的生成脚本覆盖当前实现。


## B-02.6最终交接（2026-10-08）

B-02.6及B-02整体闭环已完成。实际联合批次b026-20261008-220506、入口docs/tests/run-b02-acceptance.ps1、总报告target/acceptance/b026-20261008-220506/report.json为PASSED；15项测试/固定JDK21构建、双B库V4与最小权限/跨库拒绝、真实核心及在线/离线Edge、原签名/ACL基线通过。新增ACK窗口只在独立验收包：真实A结果落库后halt(86)，新B进程重收相同回执且Inbox一条/确认状态不变；业务8次重试保持。正常包不包含验收/Flyway，产物SHA256、环境全恢复/端口释放/默认Java8均存证。

唯一过程文档D:/Java/zj-market/docs/b02-development.md第15节：统一命令/矩阵、第15.2节B-01技术前置及遗留、第15.3节B-03字段输入及价格不保留语义；路线图已按证据更新。源码仍D:/Java/zj-market-b01、codex/b-01未提交工作树，不合并/清洗或覆盖旧改动。B-03尚未开展，实际开始时另建唯一B-03过程文档，后续方案取舍继续交用户。生产部署、正式TLS、备份、监控及压测目标明确留待后续，不宣称已上线。

此次联合验收与交接复杂度中等，三步均通过；B-02总体实现高复杂度。完整实际证据与边界以唯一B-02过程文档为准。

## 当前Git归档与开发入口（2026-10-08）

本节覆盖前文历史记录中“未提交/合并”“原目录只有初始工程”的当前状态：用户已授权本地提交与合并，B-02源码提交为9d75f82，分支b-02已快进合并到master。D:/Java/zj-market现在包含完整模块工程、前端、脚本及唯一docs/b02-development.md和b02-http-api.json；D:/Java/zj-market-b01保留在b-02。后续在主目录打开IDE时使用master的完整Maven工程；本机凭据继续外部注入，不随Git复制或提交。

原目录14个文件及索引已保留在被忽略的target/merge-b02-20261008-224649，SHA256验证通过；主分支保留最新路线图、完整阶段过程/HTTP契约与交接记录。仅配置B仓库作者ZJ，未推送远程或开展B-03。实际业务验收仍为b026-20261008-220506的PASSED结果，不将Git归档视为重新执行联合验收。本次复杂度中等，按保全、提交、快进、文档补齐四步完成。
