# UX 独立环境与 UX-00 运行说明

最新状态（2026-10-18）：UX-01 已在现有 `D:\Java\zj-market-ux` 工作树完成本机验收，运行 Web 镜像为 `zj-market-ux/web:ux01-20261018-02`；旧站继续由 `D:\Java\zj-market-stable\scripts\stable.ps1` 管理。下述 ST-04 环境建立过程保留为历史基线，后续 UX-02 不再重建分支、空卷或稳定站。

当前本机 B 新版工作树为 `D:\Java\zj-market-ux`（`codex/storefront-ux`，从 ST-01 B 提交 `e18f4479` 分出），A 继续使用 `D:\Java\group-buy-market` 已冻结源码与 ST-01 固定镜像，不另建 A 工作树。旧站继续由 `D:\Java\zj-market-stable\scripts\stable.ps1` 管理；UX 项目为 `zj-market-ux`，入口 `https://zj-market-ux.test:8446`。两站使用不同域名、浏览器配置、五网络、五数据卷和整套新凭据；UX 不读取主站备份，也不连接主站数据库和 Broker。

本机 UX 的 A/B 镜像复用 ST-01 已验内容 ID，但各自启动独立容器；ST-04 Web 基线镜像为 `zj-market-ux/web:st04-20261017-02`。继承的 `group_buy_market_b06`、`zj_market_b06` 库名及 `-b06` Topic 后缀只是项目内逻辑名，实际网络和存储属于 UX，不是主站数据。UX 演示数据由空卷显式迁移与种子生成，两条 TD-01 A 发现索引已定向追加；本机没有克隆主站待办或历史支付退款。

日常检查先分别运行旧站 `ready` 和 UX `python -B scripts/b06-deployment.py ready`，再运行 `python -B D:\Java\zj-market\docs\tests\verify-st04-isolation.py`。后者只读核对容器、挂载、端口、网络、数据卷和内部地址。UX 当前模式另见 `.local/b06/control/state.json` 的 `mode=open`、`phase=READY`；`ready` 现在还以专用 CA 读取实际 HTTPS 网关模式，明确输出 `UX_GATE_OPEN` 或 `UX_GATE_MAINTENANCE`；`status` 同时报已保存状态和实际模式，`FAILED_GATE_CLOSED` 不会被当作开放就绪。运行 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Java\zj-market-ux\scripts\open-st04-ux.ps1` 会在确认 UX 已开放后，将 UX 专属 CA 加入当前用户信任库并以 `.local/st04/browser-profile` 打开专用 Edge；浏览器配置目录已单独收紧 ACL。旧站浏览器仍使用稳定目录的独立配置。无界面 Edge 已实测 UX 页面与主机 Cookie 隔离；该测试跳过浏览器证书错误，严格 TLS 另由各自 CA 的 Node 探针验证。不要用相同域名的不同端口替代此配置。

如需暂时释放资源，只在 UX 工作树运行 `python -B scripts/b06-deployment.py stop`；该命令保留 UX 卷，不操作 `zj-market-b06`。恢复需在确认 UX 配置和镜像标签后执行 `python -B scripts/b06-deployment.py open`，随后核对两站和隔离报告。已开放时日常只用 `ready/status`；重复 `open` 现只核对、不重建，误用 `start` 会在任何网关变更前拒绝。容量不足也会在变更前拒绝；若确需切换模式，先受控停止 UX 释放内存，再启动目标模式。稳定站日常操作只用其独立入口，切勿对原 TD-06 主站脚本执行 `start`。

从冻结 ST-01 源码重建另一套环境时，先检查目标路径、分支、子网 `10.250.50.0/24`～`10.250.54.0/24`、8446 端口和内存，再从原 B 仓执行 `scripts/st04-prepare-ux.py`；随后执行 `scripts/st04-fix-ux-logging.py`。这两个一次性准备器会拒绝非 UX 目标和部分重复写入。之后在 UX 工作树生成新凭据、构建独立版本 Web 镜像、初始化空库、应用 `scripts/st04-ux-indexes.py`，最后开放。实际初始化日志保存在 UX 忽略目录 `.local/b06/control/logs`；不要复制本机已有 `.local` 到 Git 或另一机器。当前 UX 服务内存上限合计约 3 GiB，Docker 预留 256 MiB；若容量门禁不通过，先停 UX 并核对资源，不改用主站组件。

本轮验收见 [ST-04 摘要](../../docs/tests/st04-acceptance.json)和[隔离方案](../../docs/stable-release-worktree-isolation-plan.md)。ST-04 只建立隔离开发与测试环境，是后续 UX-00 的历史基线。

ST-05 接续（2026-10-17）：ST-04 UX Web 镜像已保存到 B 项目受限私有交付快照，镜像 ID 为 `sha256:449d818ce60072922cd4b41dc0d5011bdcd5b9cee58ba84d5d23e9d2abb914bb`。该快照不含 UX 数据卷；旧版完整交付边界见 `D:\Java\zj-market\deploy\st05\README.md`。

UX-00 接续（2026-10-18）：切换前在 UX 忽略目录 `.local/ux00/backups/ux00_20261018_01` 保存五个 UX 数据卷与私有运行输入，52 文件逐项哈希通过；它是本机冷备，不是异地恢复证明。新 Web 镜像归档 `.local/ux00/images/web-ux00-20261018-01.tar` 的 SHA-256 为 `5DC8D1B1C73672E79B188AF2E6C0CF70E948BA78574BE63F826F46F9AA5B4468`，Image ID 为 `sha256:f99697aaa392b3fa982e39b8ba379eae5b5d162962861f04aeaed4ce1186ee32`。前端非 JSON／坏 JSON 等异常得到中文提示且不自动重放写请求；网关 `GET /api/v1/system/status` 只返回当前模式，维护拦截和自身上游故障返回 JSON。真实维护→开放验收通过，旧站始终 `READY`。测试和下一阶段见[UX 方案](../../docs/storefront-experience-optimization.md)。

UX-01 接续（2026-10-18）：用户展示品牌改为“正经商城”，账号中心固定 `/account`，运营和购物导航分离；新镜像 `zj-market-ux/web:ux01-20261018-02` ID `sha256:e95c5c1b4fc07d788c55dd5b5507139481345fb62bacfcfe05da7780c825bedc`。本机镜像归档 `.local/ux01/images/web-ux01-20261018-02.tar` SHA-256 `BA03E9CAE432D9C4D63BB9E82289DF201CEFFCD8E165303AF0311CAFF74ACD8C`；UX-00 镜像仍可作为 Web 回退点。当前 `.local/b06/build/release.env` 的 `B06_WEB_IMAGE` 已指向 UX-01；切换其他版本前须受控停止 UX 并核对容量。实际开放状态、旧站隔离、桌面／手机浏览器与路由回归均已通过，证据及后续 UX-02 范围见[UX 方案](../../docs/storefront-experience-optimization.md)。UX-00～05 只要求本机 Windows＋Docker 验收。
