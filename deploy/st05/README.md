# ST-05 本机交付与恢复约定

旧站当前运行入口为 `D:\Java\zj-market-stable\scripts\stable.ps1`，UX 测试站为 `D:\Java\zj-market-ux`。本阶段在 B 仓忽略目录 `target/stable-isolation/st05_20261017_02` 建立离线交付快照：`public/` 是可审阅的脚本、配置模板、脱敏清单和 ST-03／04 证据；`private/` 保存稳定版固定 release、37 份私有输入、六个镜像归档及 UX 的本机私有材料和 Web 镜像归档。`public-manifest.json`、`private-manifest.json` 和最后写入的 `COMPLETE.json` 记录逐文件哈希；私有清单及材料留在受限目录，不进 Git。公开索引为 [ST-05 清单](../../docs/st05-delivery-manifest.json)，验收见 [ST-05 摘要](../../docs/tests/st05-acceptance.json)。

日常使用**当前独立运行目录**，无需 Maven 或 Vite：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Java\zj-market-stable\scripts\stable.ps1 -Action status
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Java\zj-market-stable\scripts\stable.ps1 -Action ready
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Java\zj-market-stable\scripts\stable.ps1 -Action start
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Java\zj-market-stable\scripts\stable.ps1 -Action open
```

`start` 在已就绪时只做核对，不重建；`open` 使用稳定站专用 Edge 配置。需要主动停机时，单独运行同一入口的 `-Action stop`；它先关新写入入口再停七服务，保留五原卷。UX 检查、暂停及浏览器入口见 [UX 说明](../ux/README.md)。主站和 UX 不能互用 Compose 命令、配置或浏览器目录。

离线核验可在不改运行栈的情况下执行：

```powershell
python -B D:\Java\zj-market\scripts\stable-release\verify-st05-delivery.py D:\Java\zj-market\target\stable-isolation\st05_20261017_02
python -B D:\Java\zj-market\docs\tests\verify-st04-isolation.py
```

若普通 `ready` 失败，先运行 `status`，核对 Docker Desktop Linux 引擎、七服务健康和 `state/lifecycle.jsonl`；不得用旧 TD-06 主站入口重复 `start`，也不得对原五卷执行 `down -v`。切换中失败由稳定控制器关闭新入口并记 `FAILED_GATE_CLOSED`；按 [稳定站运行说明](../stable/README.md)查原因并恢复同一固定镜像和卷。若只是 UX 资源压力，可仅在 UX 工作树运行 `python -B scripts/b06-deployment.py stop`，保留旧站。恢复时先检查隔离配置与独立标签，再开放 UX。

离线快照是**本机固定材料交付**，不是第二个可同时启动的主站。快照未携带在线卷，也未携带 ST-03 `adoption.json` 授权；不能直接用其控制器接管现有卷。六个稳定镜像归档可逐个核验 SHA-256，并在受控恢复环境用 `docker load -i` 导入；只有镜像 ID、私有输入、schema、网络／卷身份和最新业务备份都核对后，才能按单独灾难恢复方案接管。ST-03 冷备 `st03_20261016_04` 已重新验哈希，但它早于随后发生的真实模拟交易，**不是当前实时恢复点**，不可覆盖在线卷。当前主站若出现新的交易，回退优先兼容代码或前向修复；数据库恢复必须另定停写一致性点并核对资金、库存、Outbox／Inbox 与退款义务。跨主机复制、异机恢复、Linux 部署和镜像仓库上传未在 ST-05 验收，不能由本机清单推断已经完成。

本阶段交付检查使用 `scripts/stable-release/build-st05-delivery.py`，目标目录存在时拒绝覆盖。`private/ux-materials` 仅供本机 UX 继续开发或离线保管，不含 UX 数据卷，不能宣称 UX 业务数据可从中恢复；其中 demo 账号、密钥和配置只在受限私有目录内。公开 Git 内容不含这些文件。ST-05 完成后，商城体验改造仍从 UX-00 开始，正式站升级须另走“UX 独立验收→当前数据备份→兼容核查→受控替换→验收”。
