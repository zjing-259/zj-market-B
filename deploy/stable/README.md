# 独立稳定版运行入口（CAT04 发布，CAT 系列已验收）

当前验收口径补充（2026-10-21）：CAT-01.1～01.5 已完成已约定范围，交付证据复核通过；首页仍保留 B06 demonstration product（就绪探针依赖）和 B063 b063-normal01 success（精确归属待核对）。解除探针依赖与核对归属后的商品整理尚未实施，不能宣称全部展示商品已整理。本批待办为零也不代表历史核对／人工复核／待履约全系统清空。本次 Docker 未启动，未重新检查在线首页、商品状态或数据库快照；下文运行数量和 READY 记录均取自已注明的历史验收，日常使用时须实际执行就绪检查。详见 [范围与剩余展示收尾](../../docs/catalog-optimization.md)。

主站现为 `cat04-stable-20261020-01`／正经商城新版，CAT-01.4 开始时的原 66 笔订单及原义务保持，六件日用品在售，52 件确认历史样本和 CAT05 七件专用样本已下架，2 件保留；CAT05 新增五笔已验订单，当前总计 71 单。`zj-market-b06` 已于 2026-10-16 从 `D:\Java\zj-market-stable` 接管，沿用原五卷、五网络及固定镜像。当前日常入口为 `D:\Java\zj-market-stable\scripts\stable.ps1`；原 `td06-environment.py`、`td06-main-release.py` 和旧浏览器入口对主站已设置交接门禁。ST-02 原候选仍位于已忽略的 `target/stable-isolation/st02_20261016_04/bundle`，仅作历史材料，不能用于当前主站启停。

先启动 Docker Desktop 的 Linux 引擎，再在 Windows PowerShell 使用：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Java\zj-market-stable\scripts\stable.ps1 -Action status
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Java\zj-market-stable\scripts\stable.ps1 -Action ready
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Java\zj-market-stable\scripts\stable.ps1 -Action start
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Java\zj-market-stable\scripts\stable.ps1 -Action open
# 仅需要主动停机时单独执行；保留全部原卷
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Java\zj-market-stable\scripts\stable.ps1 -Action stop
```

`status` 只读；正常应为 `READY` 且 `adopted:true`。`start` 在已就绪时只做核对，不重建容器。`open` 在 `ready` 通过后使用稳定版专属 Edge 配置目录。`stop` 先切维护网关，再按依赖停止七服务。失败时保持网关关闭并查看 `state/lifecycle.jsonl`、`state/state.json` 与容器真实状态；不要手改 `adoption.json` 或把旧备份覆盖在线卷。完整接管与模拟交易证据见[ST-03 摘要](../../docs/tests/st03-acceptance.json)。

独立目录当前发布为 `releases/cat04-stable-20261020-01`，私有输入在 `private/cat04-stable-20261020-01`，入口指向新清单。原 `releases/td06-stable-20261016-01`、原 private 清单和 ST 镜像归档保持原字节；state 保存当前生命周期，images 保存已验镜像；最新升级前冷备为 `backups/cat04-main-20261020-01`；`backups/ux05-main-20261019-01` 为上一发布历史冷备，ST-03 冷备仅作历史。升级后已有新交易，禁止旧备份覆盖在线卷。私有配置、备份与浏览器状态仅授权当前用户、SYSTEM 和 Administrators；历史失败批次留存供诊断，不能当作最新恢复点。

部署包生成器从 TD-06 已验的 `compose-on.json`／`compose-maintenance.json`、ST-00 实际挂载与 ST-01 固定镜像清单取材，逐字节复制并校验私有输入，不覆盖已有批次。七个常驻服务和已退出的 MQ 权限辅助服务均固定实际 Image ID；五个原数据卷和五个网络声明为 `external: true`。运行模板只引用包内 `private`，没有 `build:`、源码挂载、旧工作树路径或自动 pull／迁移／旧备份恢复。旧备份原件继续保留；新启动门禁改用包内固定清单、原卷创建时间、网络 ID、schema／Flyway／索引和只读业务探针，不再调用旧备份控制器。

以下为 ST-02 历史构建方法，日常运行不调用：

```powershell
python -B scripts/stable-release/build-st02-bundle.py --root D:\Java\zj-market\target\stable-isolation\st02_new_batch\bundle
python -B scripts/stable-release/verify-st02-bundle.py D:\Java\zj-market\target\stable-isolation\st02_new_batch\bundle
```

ST-02 原候选可只读查看历史状态：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Java\zj-market\target\stable-isolation\st02_20261016_04\bundle\releases\td06-stable-20261016-01\stable.ps1 -Action status
```

原候选仍显示 `adopted:false`。ST-03 独立目录的 `state/adoption.json` 记录最新备份批次和清单哈希；它只授权已核验的生命周期，不替代备份本身。新控制器已修正维护网关识别、首次接管强制重建以及 B 开放配置先于 web 开放的顺序。

ST-02 历史候选的阶段验收见[摘要](../../docs/tests/st02-acceptance.json)；当前现场验收以 [UX-05 最终验收](../../docs/tests/ux05-acceptance.json)为准。

UX-05 当前操作仍为 `stable.ps1 -Action ready/status/start/stop/open`；日常启停只依赖独立稳定目录，A/B 镜像与 schema 未改。两站隔离使用 `python -B D:\Java\zj-market-ux\scripts\cat03-isolation.py`，允许共享已验 Web 内容，仍严格检查独立容器、卷、网络、域名和端口。

升级前冷备为 `D:\Java\zj-market-stable\backups\ux05-main-20261019-01`，含双库逻辑导出、五卷冷归档、原配置／发布／入口／接管凭据与逐文件哈希。它是升级前冷点，之后已产生新交易，禁止覆盖在线卷。独立 UX 已实测兼容旧 Web 退包再恢复新版，当前订单／资金／退款／库存／账本不变。TD-06／ST 历史材料保持原字节；新增主站归档 `images/web-ux05-20261019-01.tar`，SHA-256 `F5B06A0AC7A9557BBA88C48ED7612243DB95F5BD7C9BB4FC3205214C61456622`。

需要兼容退包时保留当前数据，使用已验源码入口 `python -B D:\Java\zj-market-ux\scripts\ux05-release.py rollback --batch ux05-main-20261019-01`：它先停写，复用当前五卷及原固定镜像／配置，再恢复原入口。该发布变更工具在 UX 分支，日常启停不依赖它。失败／部分启动先按日志诊断并保持入口关闭；resume 仅允许已核验冷备、全部服务停止的冷点，运行中会拒绝。不得以降级数据库或旧备份覆盖使验收通过。

2026-10-20 CAT-01.3 接续：主站发布／商品／库存未变，UX 单独启用 CAT 商品图片镜像；两站当前 Web 内容不同。日常隔离改用 UX 工作树 `scripts/cat03-isolation.py`，旧 UX-05 隔离源码与验收保留历史哈希，不作为新镜像实时断言。主站商品替换仍待 CAT-01.4。


CAT-01.4 当前发布与商品维护（2026-10-20）：

- 运行清单：[cat04-release.json](../../docs/cat04-release.json)；[实际商品／下架／保留 ID](../../docs/cat04-main-products.json)；[验收报告](../../docs/tests/cat01-4-acceptance.json)。Web 内容固定为 CAT03 已验 `sha256:f85131ff30aa0835dbbf5d52184596ed646e765af3fa244f5a1ba2ee9fbfc862`，归档位于稳定目录 `images/web-cat04-20261020-01.tar`。原 A/B 镜像、schema、Flyway、五原卷／网络未变；主站 nginx、CA、账号及内部配置保持原值。
- 日常健康检查仍用顶部独立稳定入口；两站隔离用 UX 工作树 `python -B scripts/cat04-isolation.py`。不要执行历史 UX05/CAT01/CAT03 镜像断言作为当前发布门禁。
- 本批在 UX 源码目录执行的主站准备入口为 `node scripts/cat04-products.mjs prepare` → `python -B scripts/cat04-configure.py` → `node scripts/cat04-products.mjs publish` → `node scripts/cat04-products.mjs retire`。本批已完成；重跑只核对原记录。不要删除 `.local/cat/cat01-4-20261020-01/fixture.json` 或换新入库键，交易后库存发生变化时校验会拒绝，不能重置余额绕过。
- `retire` 仅接受 CAT-01.1 精确 52 ID 且重新核对原 fixture 哈希，保存新商品就绪证据后才逐件编辑；保留完整字段和当前 expectedVersion。冲突、创建结果未知或原操作状态不明必须核对原记录，不重新 POST 替代商品／库存，不按名称扩大范围。
- 六件新商品各 20 件入库都有原操作记录与唯一流水；正常展示商品本轮未产生交易。历史 66 单、185 流水和原库存保持，只增加 6 条入库流水（共 191）。原 24 个 RECONCILING、1 项未终结工作、10 ACTIVE 隔离、13 review、28 待履约保持，未借本批清理。
- 最新冷备含双库逻辑备份、五原卷以及旧发布／私有输入副本，`COMPLETE.json` 绑定清单哈希；它是本批整理前的恢复资料，不能覆盖当前在线卷。旧 `releases/ux05-stable-20261019-01` 和 TD06 发布均未改。
- 资源发布工具 `python -B scripts/cat04-release.py ready` 核对本发布；`rollback --batch cat04-main-20261020-01` 只允许健康已接管新发布先闭网关停机，再以当前数据退回旧兼容镜像与配置，不恢复数据库或卷。旧 Web 不含六张新图片，退包会显示原占位，之后需恢复 CAT04 资源；不要将退包作为商品回滚。冷点中断才使用 `resume --batch cat04-main-20261020-01`，要求七服务全停且完整备份哈希通过，运行中拒绝恢复。
- 浏览器验收 `node scripts/cat04-browser.mjs` 只读；最终核对 `python -B scripts/cat04-acceptance.py` 对本批基线逐项检查。以后合法新交易会使该冻结基线检查失败，应建立新阶段证据，不能重写 CAT04 报告或补回库存。专用交易与本批样本收尾归 CAT-01.5。


CAT-01.5 最终验收与日常维护（2026-10-20）：

[最终报告](../../docs/tests/cat01-5-acceptance.json)／[本批样本与原交易 ID](../../docs/cat05-main-samples.json)。主站资源发布仍为 CAT04，当前 67 件商品（公开 8／下架 59）、71 单、207 库存流水；六件日用品各库存 20，零本批订单。专用七件样本全为 OFF_SALE／版本 3／A 确认，五笔交易实付 360／全退 180 元，本批待支付确认／退款／库存释放为 0。原 66 单和 191 流水、原库存及核对／隔离／待履约保持，新增两笔成团待履约和一个空取消团按原边界保留，不强行清理。

在 `D:\Java\zj-market-ux` 查看本批只读计划：

```powershell
python -B scripts/cat05-run.py --batch cat01-5-20261020-01
```

默认动作是 `plan`，不登录、不写业务。当前已验批次不可重跑 `all` 或 `browser`，不可重新发布。健康检查仍用稳定版 `ready`、UX `ready` 和 `cat04-isolation.py`；不要拿准备或交易验收当健康检查。

只有另一次明确授权的验收才使用**新批次**，先阅读方案、核对 Git／现场和计划，选择符合 `cat01-5-YYYYMMDD-NN` 的新编号。统一 `all --batch <新编号>` 会先保存本次主站／UX 基线，先 OFF_SALE 创建七件自有样本、原编号入库、受控只插入本批活动、确认最终版本，再真实浏览器交易／自然退款、逐单查账、留证、下架、重复收尾和最终核对。期间会在首页短暂出现专用样本，完成或失败后仅处理该批精确 ID。各小阶段在本批已逐步实测；不为测试组合入口再次产生额外交易。

实际入口与恢复：

- `cat05-run.py` 提供 `capture/prepare/configure/publish/verify/guards/stockout/browser/collect/seal/cleanup/final-browser/finalize` 显式动作，均带 `--batch`。`cat05-checks.py` 的 prepare/repeat/evidence/cleanup/sealed 检查由 all 串联；分阶段调用新批次时传递同一 `CAT_ACCEPTANCE_BATCH`，不能混批。普通 prepare 不自动补造丢失的入库编号。
- 私有 `.local/cat/<批次>/fixture.json`、浏览器 storage state、写请求记录及 evidence-lock 保留原商品 ID、购买意图、支付／库存／下架原编号和请求体。创建未知只按完整字段和创建前 ID 集合核对；不能可靠关联时停下查证，不新建替代商品或订单。未知业务结果不换键重发。
- `browser` 支持未封存失败批次的原订单／原支付根继续；进入证据封存后禁止重跑交易。集中登录遇 429 只按 Retry-After 等身份登录窗口，不重发资金或库存写入；浏览器和客户端均使用主站受信 CA，不跳过 TLS 校验。
- 成功交易后 `collect` 核对 B 订单／渠道／退款／库存唯一流水和 A 名额／收款／退款／核对确认，再 `seal`。证据文件复制封存并绑定哈希，收尾前先核对锁及精确 ID。收尾只做当前商品完整字段＋当前 expectedVersion 的 OFF_SALE 编辑，不删数据、不关闭旧活动、不延长期限、不改订单／团队终态。
- 失败批次保存原记录，可 `seal --failed --batch <原批次>` 后 `cleanup --batch <原批次>` 只下架已明确归属的商品；未知创建结果必须另列原记录供核对，不能把未确认 ID 随便归给本批。all 在失败时尝试留证和本批收尾；依赖不可用导致收尾失败时保留 cleanup-pending 和原键，恢复依赖后重复 cleanup。失败封存不能冒充成功最终验收，未结金融／释放义务必须继续核对。
- `cleanup` 可重复，已下架只核对，不再次增版；sealed 门禁阻止新建、入库和重新上架，正常六件及探针不能被本批清理。下架不阻断合法原单查询、付款、取消或退款恢复，未完成原单继续自然收敛。
- `final-browser` 只读确认公开集合、实际图片和六件报价、下架原单；`finalize` 对本批原基线和交易事实严格核验。以后合法新交易可能改变快照，不能覆盖当前 CAT05 报告或重置库存让旧基线重新通过，应创建新观察／任务证据。
- 原 UX05 写入工具没有 CAT 样本收尾，现 prepare/browser 入口明确拒绝；其只读查账和历史 Git 源码／证据保留。CAT03 为 UX-only，CAT04 为正常商品及精确旧样本清单，不能拿来制造新交易或批量扩大收尾。

本阶段未新增冷备或发布，CAT04 冷备是整理前历史恢复资料；CAT05 已有新交易，严禁用旧备份覆盖在线卷。原 24 RECONCILING 团队、1 未终结工作、10 ACTIVE 隔离、13 review 及 28 原待履约继续按原业务维护；本批新增待履约不等于真实发货，无付款／预留的取消空团保留原自然状态。

2026-10-21 交付复核：已解除暂停，Docker 启动后主站 READY、两站隔离和原容器身份通过；主站及 UX 全业务语义快照与 CAT05 最终验收时一致。已验代码／证据哈希及交付差异复核通过，源码和验收的暂停提交已推送，旧报告保持不变。本次仅只读复核和文档收尾，不重跑已封存交易；CAT-01.1～01.5 已完成，继续使用上述日常健康及原记录恢复入口。
