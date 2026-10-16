# ST-03 独立稳定版运行入口

主站 `zj-market-b06` 已于 2026-10-16 从 `D:\Java\zj-market-stable` 接管，沿用原五卷、五网络及固定镜像。当前日常入口为 `D:\Java\zj-market-stable\scripts\stable.ps1`；原 `td06-environment.py`、`td06-main-release.py` 和旧浏览器入口对主站已设置交接门禁。ST-02 原候选仍位于已忽略的 `target/stable-isolation/st02_20261016_04/bundle`，仅作历史材料，不能用于当前主站启停。

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

独立目录分为 `releases/td06-stable-20261016-01`（固定镜像、Compose 模板与工具）、`private`（37 份实际运行配置／证书／账号与哈希清单）、`state`（可变生命周期、浏览器资料）、`images`（六个 ST-01 镜像归档）和 `backups/st03_20261016_04`（最新一致性冷备）。私有配置、备份与浏览器状态仅授权当前用户、SYSTEM 和 Administrators；历史失败批次留存供诊断，不能当作最新恢复点。

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

ST-02 历史候选的阶段验收见[摘要](../../docs/tests/st02-acceptance.json)；当前现场验收以 ST-03 摘要为准。
