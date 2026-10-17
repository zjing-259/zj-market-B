# ST-04 UX 隔离环境

当前本机 B 新版工作树为 `D:\Java\zj-market-ux`（`codex/storefront-ux`，从 ST-01 B 提交 `e18f4479` 分出），A 继续使用 `D:\Java\group-buy-market` 已冻结源码与 ST-01 固定镜像，不另建 A 工作树。旧站继续由 `D:\Java\zj-market-stable\scripts\stable.ps1` 管理；UX 项目为 `zj-market-ux`，入口 `https://zj-market-ux.test:8446`。两站使用不同域名、浏览器配置、五网络、五数据卷和整套新凭据；UX 不读取主站备份，也不连接主站数据库和 Broker。

本机 UX 的 A/B 镜像复用 ST-01 已验内容 ID，但各自启动独立容器；Web 镜像为 `zj-market-ux/web:st04-20261017-02`。继承的 `group_buy_market_b06`、`zj_market_b06` 库名及 `-b06` Topic 后缀只是项目内逻辑名，实际网络和存储属于 UX，不是主站数据。UX 演示数据由空卷显式迁移与种子生成，两条 TD-01 A 发现索引已定向追加；本机没有克隆主站待办或历史支付退款。

日常检查先分别运行旧站 `ready` 和 UX `python -B scripts/b06-deployment.py ready`，再运行 `python -B D:\Java\zj-market\docs\tests\verify-st04-isolation.py`。后者只读核对容器、挂载、端口、网络、数据卷和内部地址。UX 当前模式另见 `.local/b06/control/state.json` 的 `mode=open`、`phase=READY`；`ready` 本身只验数据库和权限，不证明 Web 已开放。运行 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Java\zj-market-ux\scripts\open-st04-ux.ps1` 会在确认 UX 已开放后，将 UX 专属 CA 加入当前用户信任库并以 `.local/st04/browser-profile` 打开专用 Edge；浏览器配置目录已单独收紧 ACL。旧站浏览器仍使用稳定目录的独立配置。无界面 Edge 已实测 UX 页面与主机 Cookie 隔离；该测试跳过浏览器证书错误，严格 TLS 另由各自 CA 的 Node 探针验证。不要用相同域名的不同端口替代此配置。

如需暂时释放资源，只在 UX 工作树运行 `python -B scripts/b06-deployment.py stop`；该命令保留 UX 卷，不操作 `zj-market-b06`。恢复需在确认 UX 配置和镜像标签后执行 `python -B scripts/b06-deployment.py open`，随后核对两站和隔离报告。此控制器继承 B-06 的生命周期行为，已就绪时不要把重复 `open` 当作普通健康检查；UX-00 会统一处理前置拒绝。稳定站日常操作只用其独立入口，切勿对原 TD-06 主站脚本执行 `start`。

从冻结 ST-01 源码重建另一套环境时，先检查目标路径、分支、子网 `10.250.50.0/24`～`10.250.54.0/24`、8446 端口和内存，再从原 B 仓执行 `scripts/st04-prepare-ux.py`；随后执行 `scripts/st04-fix-ux-logging.py`。这两个一次性准备器会拒绝非 UX 目标和部分重复写入。之后在 UX 工作树生成新凭据、构建独立版本 Web 镜像、初始化空库、应用 `scripts/st04-ux-indexes.py`，最后开放。实际初始化日志保存在 UX 忽略目录 `.local/b06/control/logs`；不要复制本机已有 `.local` 到 Git 或另一机器。当前 UX 服务内存上限合计约 3 GiB，Docker 预留 256 MiB；若容量门禁不通过，先停 UX 并核对资源，不改用主站组件。

本轮验收见 [ST-04 摘要](../../docs/tests/st04-acceptance.json)和[隔离方案](../../docs/stable-release-worktree-isolation-plan.md)。ST-04 只建立隔离开发与测试环境；体验改造 UX-00～05、正式站升级、远端推送和异机部署不在本阶段。
