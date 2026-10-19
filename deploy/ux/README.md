# UX 独立环境与 UX-00 运行说明

最新状态（2026-10-19）：UX-04 已在现有 `D:\Java\zj-market-ux` 工作树完成本机验收，运行 Web 镜像为 `zj-market-ux/web:ux04-20261019-01`；旧站继续由 `D:\Java\zj-market-stable\scripts\stable.ps1` 管理。下述 ST-04 环境建立过程保留为历史基线，后续 UX-05 不再重建分支、空卷或稳定站。

UX-04 当前版本：运行 Image ID `sha256:fdd4072544a5290a3d51f58b8d1cbd83cac02bcb6eb2a20abaf9f3b3a9bbc145`，私有归档 `.local/ux04/images/web-ux04-20261019-01.tar` SHA-256 `F5B06A0AC7A9557BBA88C48ED7612243DB95F5BD7C9BB4FC3205214C61456622`，`B06_WEB_IMAGE` 指向 UX-04。UX-03 镜像和归档保留为前端回退点。控制器现按模式生成 `b.team-discovery.enabled`（开放 true、维护 false），修复 UX 实际待拼接口 404；复用原 A/B 镜像及索引。只读就绪、两站隔离和实际受信 Edge 浏览器均通过；完整验收见[UX 方案](../../docs/storefront-experience-optimization.md)。

本机演示从现有 `scripts/open-st04-ux.ps1` 打开专属浏览器，入口是 `https://zj-market-ux.test:8446`；旧站仍为 `https://zj-market.test`，不要混用两站账号、订单或浏览器配置。当前用户未信任 UX CA 时，该既有入口会加入当前用户信任库；验收不关闭证书校验。

1. 在 UX 本机私有 `D:\Java\zj-market-ux\.local\b06\control\demo-accounts.json` 查看账号：`b06operator` 用于运营；`b06buyer`、`b06buyer2` 用于两位买家。密码不写入 Git 或报告。两位买家使用不同浏览器配置或分别退出登录，避免身份混淆。
2. 买家登录后从商城首页选择 [轻行随身杯](https://zj-market-ux.test:8446/products/d6fe5415-53da-4d1d-b147-b873f554208a)（原价 99.00、拼团 89.00）或 [日常帆布袋](https://zj-market-ux.test:8446/products/08646223-48b0-407c-8e58-1ddde742824a)（原价 59.00、拼团 49.00）。图片是随 Web 交付的项目原创 SVG 示意插画；样本不提供真实发货。
3. 选择“单独开团”后核对金额，再“确认下单并去支付”。只有后台允许时才进入模拟收银台；第一位买家付款被确认后，另一位可从商品待拼列表或邀请链接加入同一团队。实际资金、库存和名额联合验收留 UX-05。
4. 本批初始库存各 20，新团有效 120 分钟，活动配置从 2026-10-19 准备时起有效 30 天。已有订单与团队不会因刷新或重跑而延长；到期按正常状态处理。运营登录后从“运营工作台”进入商品／库存／异常核对；数量或版本冲突先重读，未知结果只查询或重试原操作。

演示准备入口为 `python -B scripts/ux04-demo.py`，只允许 UX 工作树，样本索引、原商品标识与入库键保存在 `.local/ux04/demo-fixture.json`，报告在同目录。重跑复用原样本且只 INSERT 本批新 A 活动，不更新旧活动、历史快照或交易；本批发生新交易后初始库存校验会拒绝，不能以重置数据使验证通过。商品创建结果未知会停止供核对，不自动重复创建。日常仍使用 `ready/status`，不要将准备或 `open` 当普通健康检查。

当前本机 B 新版工作树为 `D:\Java\zj-market-ux`（`codex/storefront-ux`，从 ST-01 B 提交 `e18f4479` 分出），A 继续使用 `D:\Java\group-buy-market` 已冻结源码与 ST-01 固定镜像，不另建 A 工作树。旧站继续由 `D:\Java\zj-market-stable\scripts\stable.ps1` 管理；UX 项目为 `zj-market-ux`，入口 `https://zj-market-ux.test:8446`。两站使用不同域名、浏览器配置、五网络、五数据卷和整套新凭据；UX 不读取主站备份，也不连接主站数据库和 Broker。

本机 UX 的 A/B 镜像复用 ST-01 已验内容 ID，但各自启动独立容器；ST-04 Web 基线镜像为 `zj-market-ux/web:st04-20261017-02`。继承的 `group_buy_market_b06`、`zj_market_b06` 库名及 `-b06` Topic 后缀只是项目内逻辑名，实际网络和存储属于 UX，不是主站数据。UX 演示数据由空卷显式迁移与种子生成，两条 TD-01 A 发现索引已定向追加；本机没有克隆主站待办或历史支付退款。

日常检查先分别运行旧站 `ready` 和 UX `python -B scripts/b06-deployment.py ready`，再运行 `python -B D:\Java\zj-market\docs\tests\verify-st04-isolation.py`。后者只读核对容器、挂载、端口、网络、数据卷和内部地址。UX 当前模式另见 `.local/b06/control/state.json` 的 `mode=open`、`phase=READY`；`ready` 现在还以专用 CA 读取实际 HTTPS 网关模式，明确输出 `UX_GATE_OPEN` 或 `UX_GATE_MAINTENANCE`；`status` 同时报已保存状态和实际模式，`FAILED_GATE_CLOSED` 不会被当作开放就绪。运行 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Java\zj-market-ux\scripts\open-st04-ux.ps1` 会在确认 UX 已开放后，将 UX 专属 CA 加入当前用户信任库并以 `.local/st04/browser-profile` 打开专用 Edge；浏览器配置目录已单独收紧 ACL。旧站浏览器仍使用稳定目录的独立配置。无界面 Edge 已实测 UX 页面与主机 Cookie 隔离；该测试跳过浏览器证书错误，严格 TLS 另由各自 CA 的 Node 探针验证。不要用相同域名的不同端口替代此配置。

如需暂时释放资源，只在 UX 工作树运行 `python -B scripts/b06-deployment.py stop`；该命令保留 UX 卷，不操作 `zj-market-b06`。恢复需在确认 UX 配置和镜像标签后执行 `python -B scripts/b06-deployment.py open`，随后核对两站和隔离报告。已开放时日常只用 `ready/status`；重复 `open` 现只核对、不重建，误用 `start` 会在任何网关变更前拒绝。容量不足也会在变更前拒绝；若确需切换模式，先受控停止 UX 释放内存，再启动目标模式。稳定站日常操作只用其独立入口，切勿对原 TD-06 主站脚本执行 `start`。

从冻结 ST-01 源码重建另一套环境时，先检查目标路径、分支、子网 `10.250.50.0/24`～`10.250.54.0/24`、8446 端口和内存，再从原 B 仓执行 `scripts/st04-prepare-ux.py`；随后执行 `scripts/st04-fix-ux-logging.py`。这两个一次性准备器会拒绝非 UX 目标和部分重复写入。之后在 UX 工作树生成新凭据、构建独立版本 Web 镜像、初始化空库、应用 `scripts/st04-ux-indexes.py`，最后开放。实际初始化日志保存在 UX 忽略目录 `.local/b06/control/logs`；不要复制本机已有 `.local` 到 Git 或另一机器。当前 UX 服务内存上限合计约 3 GiB，Docker 预留 256 MiB；若容量门禁不通过，先停 UX 并核对资源，不改用主站组件。

本轮验收见 [ST-04 摘要](../../docs/tests/st04-acceptance.json)和[隔离方案](../../docs/stable-release-worktree-isolation-plan.md)。ST-04 只建立隔离开发与测试环境，是后续 UX-00 的历史基线。

ST-05 接续（2026-10-17）：当前 UX Web 镜像 `zj-market-ux/web:st04-20261017-02` 已单独保存到 B 项目受限私有交付快照，并实际重新导入验证 ID `sha256:449d818ce60072922cd4b41dc0d5011bdcd5b9cee58ba84d5d23e9d2abb914bb`。快照保留本机 UX 运行凭据与配置，但不含 UX 数据卷；不能据此恢复 UX 业务记录。两站隔离检查重跑通过，UX 七服务健康。交付索引和恢复边界见 `D:\Java\zj-market\deploy\st05\README.md`。UX-00 已于 2026-10-18 实施，详见下段。

UX-00 接续（2026-10-18）：切换前在 UX 忽略目录 `.local/ux00/backups/ux00_20261018_01` 保存五个 UX 数据卷与私有运行输入，52 文件逐项哈希通过；它是本机冷备，不是异地恢复证明。新 Web 镜像归档 `.local/ux00/images/web-ux00-20261018-01.tar` 的 SHA-256 为 `5DC8D1B1C73672E79B188AF2E6C0CF70E948BA78574BE63F826F46F9AA5B4468`，Image ID 为 `sha256:f99697aaa392b3fa982e39b8ba379eae5b5d162962861f04aeaed4ce1186ee32`。前端非 JSON／坏 JSON 等异常得到中文提示且不自动重放写请求；网关 `GET /api/v1/system/status` 只返回当前模式，维护拦截和自身上游故障返回 JSON。真实维护→开放验收通过，旧站始终 `READY`。测试和下一阶段见[UX 方案](../../docs/storefront-experience-optimization.md)。

UX-01 接续（2026-10-18）：用户展示品牌改为“正经商城”，账号中心固定 `/account`，运营和购物导航分离；该阶段镜像 `zj-market-ux/web:ux01-20261018-02` ID `sha256:e95c5c1b4fc07d788c55dd5b5507139481345fb62bacfcfe05da7780c825bedc`。本机镜像归档 `.local/ux01/images/web-ux01-20261018-02.tar` SHA-256 `BA03E9CAE432D9C4D63BB9E82289DF201CEFFCD8E165303AF0311CAFF74ACD8C`；UX-00 镜像仍可作为 Web 回退点。该阶段 `.local/b06/build/release.env` 的 `B06_WEB_IMAGE` 指向 UX-01；切换其他版本前须受控停止 UX 并核对容量。实际开放状态、旧站隔离、桌面／手机浏览器与路由回归均已通过，阶段证据见[UX 方案](../../docs/storefront-experience-optimization.md)。UX-00～05 只要求本机 Windows＋Docker 验收。

UX-02 接续（2026-10-18）：商品和团队购买区已改为“单独开团／加入此团队 → 确认下单并去支付 → 原订单进度”；报价变化须重新确认，写结果未知只查原意图，只有后端开放支付能力才显示收银台入口。该阶段 `.local/b06/build/release.env` 的 `B06_WEB_IMAGE` 指向 `zj-market-ux/web:ux02-20261018-02`，运行 Image ID `sha256:00fbd940be3d924e36e9b29c671490623e5ab63c27d3c194a73e8d7c6b236d4c`。本机私有归档 `.local/ux02/images/web-ux02-20261018-02.tar` SHA-256 `98BCCEF4A86201F5322A8EEB2325B2961A2FE9A92A11F40D0CCA99E5FEDA1997`；UX-01 镜像及归档保留作回退点。日常只用 `ready/status` 检查，切换版本先受控停止 UX。真实页面登录、商品深链接、无自动建单、手机布局、旧站 READY 和隔离检查通过。完整用例与 UX-03 范围见[UX 方案](../../docs/storefront-experience-optimization.md)。

UX-03 接续（2026-10-19）：该阶段 `.local/b06/build/release.env` 的 `B06_WEB_IMAGE` 指向 `zj-market-ux/web:ux03-20261019-01`，实际 Image ID `sha256:c913469d339811c1928b5f914914b9341e3b770614d57a52fa4420964b478ccf`。本机私有归档 `.local/ux03/images/web-ux03-20261019-01.tar` SHA-256 `5073011631AAB9F267B80657183B4EC8B75EB0066B7D123640C2054370B4D07D`；UX-02 镜像及归档保留作回退点。收银台、订单和退款页面验收结果见[UX 方案](../../docs/storefront-experience-optimization.md)。首次切换因主机可用内存低于 1.5 GiB 在开放前拒绝，资源恢复后独立 UX 站开放成功；日常仍只用 `ready/status` 检查。旧站 READY、实际网关 OPEN、两站隔离及真实订单只读页面通过；UX-05 仍负责真实新交易联合验收。
