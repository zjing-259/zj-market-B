# 独立稳定版运行入口（CAT-01.4 当前发布）

主站现为 `cat04-stable-20261020-01`／正经商城新版，CAT-01.4 开始时的原 66 笔订单及原义务保持，六件日用品在售，52 件确认样本已下架，2 件保留。`zj-market-b06` 已于 2026-10-16 从 `D:\Java\zj-market-stable` 接管，沿用原五卷、五网络及固定镜像。当前日常入口为 `D:\Java\zj-market-stable\scripts\stable.ps1`；原 `td06-environment.py`、`td06-main-release.py` 和旧浏览器入口对主站已设置交接门禁。ST-02 原候选仍位于已忽略的 `target/stable-isolation/st02_20261016_04/bundle`，仅作历史材料，不能用于当前主站启停。

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
