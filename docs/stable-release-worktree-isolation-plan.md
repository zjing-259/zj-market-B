# 旧版稳定运行与新版工作树隔离实施方案

状态：ST-00 已于 2026-10-16 完成只读盘点与范围冻结；ST-01～ST-05 待实施。尚未提交源码、保存镜像、创建隔离工作树或切换部署。

## 1. 目标与已知现状

在实施[商城体验优化](storefront-experience-optimization.md)期间，旧版仍可正常使用；新版源码、构建和测试不影响旧版交易。旧版固定为当前 TD-06 主站版本，而非更早的 B-06 或候选 8445 版本。

当前主站已经运行构建后的 A/B/web Docker 镜像，并非实时读取 Vue/Java 源码。但启动控制器、Compose、外置配置、证书、校验工具和私有发布状态仍依赖工作树。仅提交 Git 或新建 worktree，不能解除这些运行依赖。

核查依据：`scripts/td06-environment.py`、`scripts/td06-main-release.py`、`scripts/open-team-discovery-browser.ps1`、[TD-06 部署说明](../deploy/td06/README.md)、[发布清单](team-discovery-td06-release.json)。实施时重新核对现场，不把本文当作实时健康报告。

当前关键路径：

| 用途 | 路径／标识 |
|---|---|
| A 源码 | `D:\Java\group-buy-market` |
| B 源码 | `D:\Java\zj-market` |
| 主站 Compose 项目 | `zj-market-b06`，入口 `https://zj-market.test`，本机 443 |
| 主站私有发布控制资料 | `D:\Java\zj-market\target\team-discovery\td06_2_main_20261015_01` |
| 历史脚本、证书、账号及备份依赖 | `D:\Java\zj-market-b-06` 下相关文件；不是可直接删除的废弃工作树 |
| 历史候选 | 8445，独立数据与旧候选镜像；本次不覆盖 |

## 2. 交给 AI 的执行约束

1. 先执行本方案的版本隔离，再进入 UX-00～UX-05。每阶段记录实际文件、命令、结果和未解决项；未验收不得标为完成。
2. 执行前读取适用的 AGENTS.md、Git 状态和 worktree 列表，保留现有修改。本文创建只授权规划；未来用户要求执行本方案时，才落实其中提交、打标记、部署与工作树操作。推送远端、上传镜像不是本方案默认任务。
3. A、B 分别审查和提交当前功能基线；不得 `git add .` 后盲目提交。凭据、私钥、会话、备份、私有发布记录不进 Git。
4. 保留原主站项目名、五个数据卷及其业务数据。禁止 `down -v`、清卷、用旧备份覆盖当前数据、直接改订单／支付／退款事实。
5. 原 TD-06 发布清单、源码锁和验收报告保留原字节。新增任务文档造成旧全量归档检查差异时，解释差异并生成新的隔离交付报告，不重写历史证据使检查变绿。
6. 不为隔离工作修改业务契约、价格、库存、支付或退款规则。正式站仍是“知集”旧版；“正经商城”改名在 UX 新版实施。
7. 当前控制器重复 start 的前置条件失败可能进入维护处理；迁移期间禁止把 start 当通用修复命令。新控制器必须修复此生命周期问题，并验证维护／开放状态。

## 3. 目标布局

```text
D:\Java\group-buy-market           A 原仓库，保存已提交基线
D:\Java\zj-market                  B 原仓库，保存已提交基线与公开部署工具
D:\Java\zj-market-stable           独立部署目录，不是开发工作树
  releases\td06-stable-<批次>\     不可变镜像清单、脚本、配置模板、验证工具
  private\                         证书、凭据、真实配置；限制本机访问，不入 Git
  state\                           可变发布状态、日志、浏览器信任记录及配置目录
  backups\                         新的一致性备份及清单
  images\                          docker save 导出的镜像归档与哈希
  scripts\stable.ps1               固定入口，显式绑定已验收 release
D:\Java\zj-market-ux               B 新工作树，分支 codex/storefront-ux
D:\Java\group-buy-market-ux        仅当新版确需改 A 时创建
```

稳定环境沿用 `zj-market-b06` 和 443。UX 环境使用独立项目名（建议 `zj-market-ux`）和未占用端口（建议 8446），独立 MySQL、Redis、NameServer、Broker、数据卷、配置、凭据和浏览器目录。沿用相同 MQ Topic 名只允许在独立 Broker 中；禁止误连主站 Broker、数据库或 A 服务。

上述目录和入口均为待实现设计。发布工具源码放在 B 仓库 `scripts/stable-release/`，配置模板放在 `deploy/stable/`；独立部署目录只接收经校验的发布副本，不依赖开发工作树。

## 4. 实施小阶段

### ST-00：盘点与冻结范围

步骤：

1. 检查两仓状态、分支、HEAD、所有工作树及未跟踪文件，区分功能源码、文档、公开证据、私有运行资料。
2. 只读采集当前七个容器实际 Image ID、项目标签、端口、网络、卷、挂载、配置来源及健康状态，对照 TD-06 清单。不能只根据镜像标签判断版本。
3. 递归追踪启动依赖：Python 导入、Node 脚本、配置模板、RPC 探针、JAR、源路径、CA、账号文件和备份校验器。现有脚本涉及宿主 JDK 21、Python/PyYAML、Node、Docker Desktop Linux 引擎；固定实际可用路径与版本。
4. 检查网关实际加载配置及新交易入口。健康检查成功不等于交易入口开放；用不会创建订单的非法请求确认 API 返回 JSON，而非 HTML 维护页。
5. 保存脱敏盘点报告和私有完整清单；任何源码与运行镜像的差异逐项解释。

验收：能够回答“运行的是哪一版、依赖哪些文件、数据在哪里”。发现主站未开放或镜像不匹配时先定位，不直接换镜像。

ST-00 实测验收（2026-10-16）：[脱敏结构化报告](tests/st00-acceptance.json)为本阶段公开证据；原始 `docker inspect`、挂载绝对路径、配置来源及逐文件哈希保存在已忽略的 `target/stable-isolation/st00_20261016_01/private-inventory.json`，不得提交或公开。该快照只代表采集时点，后续交易和恢复任务会自然变化。

| 验收项 | 现场结论 |
|---|---|
| 运行版本 | `zj-market-b06` 七个常驻服务均 healthy；A/B/web 实际 Image ID 与 TD-06 发布清单一致，其余基础镜像也一致。A 当前 286 个、B 当前 355 个冻结源码文件与源码锁逐字节一致；两仓 HEAD 均早于未提交的运行源码，不能仅用 commit 表示镜像来源。另有已正常退出的 `mq-permissions` 辅助容器，ST-01 镜像归档需计入其镜像 ID。 |
| 数据位置 | 主站仍用原 `mysql-data`、`redis-data`、`namesrv-logs`、`broker-logs`、`broker-store` 五个命名卷，五网络；主机只开放 `127.0.0.1:443`。七服务的外置配置、证书、账号文件经实际挂载追踪仍来自 `zj-market-b-06` 历史目录及 B 的 TD-06 私有发布目录；不能移动或删除这些目录。 |
| 启动依赖 | 从浏览器入口、环境脚本、主站控制器及其间接脚本追踪 21 个关键文件，采集时均存在。宿主 Python 3.13.5、PyYAML 6.0.3、Node 24.16.0、Docker Desktop Linux 24.0.7 可用；默认 Java 为 8，RPC 探针依赖显式 JDK 21.0.2。 |
| 网关与只读验证 | 实际加载的 Nginx 准入配置为开放；严格 TLS 下签名发现 GET 返回 200；无认证、空 JSON 的下单 POST 返回 401/`AUTH_REQUIRED` JSON，没有生成业务订单。既有 `ready --target main443` 复核通过。 |
| 冻结边界 | 两仓当前均在 `codex/team-discovery-td00`，改动与未跟踪文件保留；B 另有六个历史工作树，A 无其他工作树。ST-00 只新增盘点程序、无效请求探针、脱敏报告及文档；无 Git 提交/标签、镜像保存、部署切换、业务写入或新工作树。 |

ST-00 风险及后续门槛：主站仍直接依赖开发/历史工作树，独立性要到 ST-03 接管后才能宣称完成；原始资金、库存及待办义务基线见脱敏报告，后续切换前必须重新采集并做一致性备份。当前控制器前置失败的维护状态风险仍在，不能把 `start` 当作诊断命令。新增 ST-00 文件使历史 `collect-td06-4-release.py check` 报 `TD-06 release manifest drift`；原 TD-06 清单、源码锁和验收报告未改写，源码锁及运行镜像的单项核对均通过。本阶段验收通过，下一阶段为 ST-01。

### ST-01：提交源码基线并保存镜像

步骤：

1. 分别审查 A/B diff 和新增文件，按明确文件列表暂存，检查 staged diff 和敏感内容，再分别提交。记录两个完整 commit ID。
2. 建立不重名的配套注解标签，例如 `stable-td06-20261016-01`，清单同时记录 A/B commit 和标签。已存在标签不得强制移动。
3. 以实际运行 Image ID 保存 A、B、web、MySQL、Redis、RocketMQ 及启动需要的辅助镜像；相同镜像只存一次。添加专用稳定标签便于识别，但 Compose 固定 ID 或已核实的仓库 digest。
4. 使用 `docker image save` 归档并计算 SHA-256，核对归档包含所需镜像；后续恢复用 load 后再次核对 ID。只增加标签不是镜像备份，容器 export 也不能替代 image save。
5. 建立 `stable-manifest.json`，记录来源提交、镜像 ID／digest、归档哈希、配置哈希、契约版本、schema／迁移历史、环境要求及历史证据引用。

验收：源码可定位，镜像可离线恢复，私有资料未提交。提交源码无需重新构建当前稳定镜像；若另外重建验证可复现性，使用新标签和隔离环境，不覆盖已验收镜像。不能仅凭提交时间宣称镜像由该提交构建，必须关联原构建证据及差异。

### ST-02：独立部署包与安全生命周期

步骤：

1. 实现部署包生成器，显式选择 release／private／state 根目录，去除对原 A/B 工作树和 `zj-market-b-06` 的运行依赖。包括间接调用的校验器、探针、Node 依赖和凭据路径；不得简单复制一个 Compose 文件即宣告完成。
2. 把需长期保留的配置、证书和校验材料复制到部署目录，私有文件不打印内容；核对内容哈希与证书指纹，限制访问。旧备份原件保留，若启动仍依赖其校验材料，要完整迁移或显式重新设计校验边界。
3. 为现有主站生成专用 Compose：七服务采用固定镜像，不含 `build:`，不挂载源码／frontend/dist／工作树 target。原五卷使用明确名称且 `external: true`，不存在就报错，不能隐式创建空卷冒充原环境。
4. 新的 `stable.ps1` 提供 `status`、`ready`、`start`、`stop`、`open`；Python 等子进程使用显式可执行路径，失败立即停止并保留脱敏原因。
5. `status` 只读；`ready` 同时核对镜像、schema、实际网关模式、核心只读链路与安全的非法写请求。`open` 仅在 ready 成功后打开稳定版专属浏览器，复用当前用户证书信任边界。
6. `start` 已正常运行则只检查并成功返回；不支持的状态拒绝且不改变网关。仅真正进入启动变更后失败才关闭新交易入口；不能吞掉恢复路径。不要把 release.json 状态直接改成 STOPPED 来绕过检查。
7. `stop` 先关闭新交易入口，再按依赖停止服务；保留全部卷。启动先数据与消息组件，再 A/B，检查后开放 web；禁止日常启动自动 build、pull、迁移或恢复旧备份。
8. 为入口加跨进程互斥，避免两个 start/stop 同时执行。不可变清单与可变生命周期日志分开，状态文件原子更新；异常中断要能核对真实容器状态后恢复。

验收：静态依赖审查确认部署包没有开发目录挂载或读取；测试重复 start、前置失败、启动中失败、停止后启动和浏览器打开。镜像缺失、卷缺失、配置漂移必须明确失败，不能自动替换版本。

### ST-03：切换旧版到独立部署目录

步骤：

1. 切换前关闭新交易入口，完成本次一致性备份，记录资金、库存和待处理义务基线。备份范围及暂停步骤遵循现有一致性工具，不能只拷运行中的数据库文件。
2. 保持原项目名和原卷，对照新旧 Compose 差异。新副本使用相同业务镜像，仅改变经审核的外置文件路径与控制入口；不得启动第二套容器同时读写主卷。
3. 用新控制器逐步接管，记录哪些容器因挂载变化被重建。外置配置只改变路径时核对内容一致。
4. 验证登录、商品、已有订单、已付待核对和退款恢复读取、待拼列表权限及 JSON 错误；使用独立新测试批次完成一次必要的模拟交易，并核对新增资金／库存流水。禁止用真实交易写操作充当每次启动的健康探针。
5. 做受控停止／启动演练；从独立目录启动并打开浏览器，确认全过程不读取原工作树。不要为了证明独立而删除旧目录。
6. 失败优先恢复原兼容部署配置和相同镜像，继续使用当前卷；不把切换前备份覆盖已经产生新交易的卷。

验收：主站可从独立目录完整启停，旧数据及恢复义务无丢失，原业务镜像 ID 不变。保留旧入口但标明已交接，后续不得同时操作同一主站。

### ST-04：创建 UX 工作树与隔离测试环境

步骤：

1. 从 ST-01 固定提交创建 B 工作树和 `codex/storefront-ux` 分支；原目录不切分支。目标目录／分支已存在时核对并复用或选择新名，不能清空。
2. 将 ST-02 的公开工具提交作为独立基础设施提交，按需引入 UX 分支，避免把运行资料带进去。A 无改动需求则不建新工作树，UX 环境复用 A 镜像但启动独立 A 容器。
3. 新建隔离 Compose 项目，独立网络及所有有状态组件、凭据与数据卷。建立无主站待办的干净演示数据最简单；若使用备份副本，必须处理未完成 Outbox／Inbox／支付退款任务及全部回调地址，确认不会访问主站后才允许消费者启动。
4. 检查端口、Dubbo 地址、MQ Broker 广播地址、数据库 URL、Redis、浏览器 cookie／会话和回调目标均指向 UX 环境。使用不同浏览器配置目录；同域不同端口并不能隔离 cookie。
5. UX 每次构建使用独立版本标签，仅更新 UX Compose。不得复用稳定标签，不改稳定目录，不接入主站数据库做联调。

验收：修改／构建／重启新版时旧站保持可用，双端读取各自数据，业务写入与消息不串环境。资源不足时可停 UX 环境，保留稳定站；不以共用生产数据组件缓解资源压力。

### ST-05：交付与后续升级约定

交付：公开脚本与模板、脱敏 `stable-manifest.json`、独立部署包、镜像归档、隔离验收报告、实际启动命令和失败恢复说明。私有包与公开 Git 内容分开。

未来 UX 升级走“新版独立验收 → 当前数据备份 → 兼容性核查 → 受控替换镜像 → 验收”。不能把 UX 测试卷覆盖主站。涉及数据库迁移时明确新旧应用兼容窗口；无法兼容则不能承诺仅切旧镜像即可回退。新交易产生后优先前向修复或兼容代码回退，数据恢复属于独立灾难恢复操作。

## 5. 完成判定

| 检查 | 必须满足 |
|---|---|
| 版本身份 | A/B commit、镜像 ID、配置、schema 均可追溯，差异有解释 |
| 文件独立 | 稳定部署不读取开发／历史工作树文件，启动不需要 Maven/Vite |
| 镜像保留 | 归档及哈希可核验，恢复后 ID 一致，普通启动不拉取新版本 |
| 数据保护 | 仍用原五卷，切换前后逐项核对原业务及待处理义务 |
| 生命周期 | 重复启动无副作用，失败状态可解释，实际维护模式可检查 |
| 新旧隔离 | 项目／端口／网络／数据／消息／浏览器会话互不串用 |
| 可操作 | Windows PowerShell 可执行，用户无需安装 pwsh 才能打开浏览器 |

## 6. 文末操作附录：旧版启动命令

### 6.1 隔离方案尚未实施：使用当前已有入口

先打开 Docker Desktop，等待 Linux 引擎就绪。在 PowerShell 执行：

```powershell
Set-Location D:\Java\zj-market
docker --context desktop-linux info
python -B .\scripts\td06-environment.py ready --target main443
```

若 ready 通过，直接打开浏览器；不要再次执行 start：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\open-team-discovery-browser.ps1 -Target main443
```

只有此前已由当前控制器正常停止、私有发布状态为 STOPPED 时才执行：

```powershell
Set-Location D:\Java\zj-market
python -B .\scripts\td06-environment.py start --target main443
if ($LASTEXITCODE -ne 0) { throw '启动失败，请先检查原因，不要重复启动。' }
python -B .\scripts\td06-environment.py ready --target main443
if ($LASTEXITCODE -ne 0) { throw '服务未就绪，暂不打开商城。' }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\open-team-discovery-browser.ps1 -Target main443
```

需要主动停止旧站时：

```powershell
Set-Location D:\Java\zj-market
python -B .\scripts\td06-environment.py stop --target main443
```

ready 失败不等于已经正常停止。Docker 重启、容器异常、网关维护或状态不一致时，先诊断，不直接运行 start 或手工改发布状态。当前脚本还有宿主 Python/PyYAML、Node 和 JDK 21 等依赖；保持原环境及历史目录，直到 ST-03 验收完成。

### 6.2 ST-03 完成后：新的独立稳定版入口

**以下是待开发接口约定，现在尚不可执行。实施 AI 必须实现并验证这些命令，再在交付报告注明生效。**

```powershell
# 已开启 Docker Desktop；查看稳定版状态
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Java\zj-market-stable\scripts\stable.ps1 -Action status

# 安全启动：已正常运行时只检查，不重复部署
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Java\zj-market-stable\scripts\stable.ps1 -Action start
if ($LASTEXITCODE -ne 0) { throw '稳定版启动未通过，请查看诊断。' }

# 检查后打开旧版浏览器
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Java\zj-market-stable\scripts\stable.ps1 -Action open

# 需要停止时单独执行，保留全部数据卷
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Java\zj-market-stable\scripts\stable.ps1 -Action stop
```

日常使用只执行需要的命令，不要将包含 stop 的整个示例一次性运行。稳定入口保持 `https://zj-market.test`；浏览器打开命令负责本机域名解析与证书信任。无需切换 Git 分支，也无需重建镜像。

## 7. 本次更新复杂程度

本次文档编写复杂度：**中等**。本轮仅新增执行方案，未提交代码、创建工作树或更改运行环境。

方案实际实施复杂度：**较高**，主要难点是历史绝对路径依赖、带状态的启动控制器与已有交易数据保护。按 **ST-00 盘点 → ST-01 源码／镜像留档 → ST-02 独立部署工具 → ST-03 原卷接管验收 → ST-04 UX 隔离 → ST-05 交付** 六个阶段执行；ST-03 通过后旧版才算真正脱离开发工作树。
