# B-01：实际 B 运行环境验证

> 历史状态说明（2026-10-10）：本文保留各实施时点的工作树、分支、未提交/未合并/未推送状态、验收批次和产物指纹；这些记录不代表当前 Git 状态。B-02、目录整理与补修、B-03及D6收尾均已包含在 `7cef241`；当前接续工作树为 `D:/Java/zj-market-b-04`，分支 `b-04`。最新进度见 [B-04开发过程](b04-development.md)及[路线图](development-roadmap.md)。历史 `.local`、`target` 和前端依赖不随 Git 复制，旧报告不作为新工作树重新验收的证据。

日期：2026-10-03（Asia/Shanghai）。状态：**本机运行环境与 RPC/MQ 最小互通已验证**；B-01 整体仍在开发中，DDD 骨架、独立数据边界和后续验收尚未完成。

## 范围与结论

在 `D:/Java/zj-market-b01`、分支 `codex/b-01` 中实施。运行的是 B 自身的可执行 JAR、入口 `cn.zj.zjmarket.ZjMarketApplication`，包含原有 WebMVC/Tomcat 配置；没有用 A 的独立 Boot4 测试夹具替代实际 B。

保留 Spring Boot **4.1.1**。先构建现有工程，再引入 A 的 Java8 契约和原始 Dubbo/RocketMQ SDK。默认 Netty **4.2.17.Final** 下，实际 B 能启动 Web 服务，但首次 TLS 查询失败；依据实际对照结果将 Netty 固定为 **4.1.118.Final**，最终不带版本覆盖参数的构建和最小链路通过。

原 IDE 指向 JDK21，原 POM 的 `java.version` 实际为17，终端默认 `java` 为 Java8。此次将工作树 POM 对齐为21；Maven 使用指定 `JAVA_HOME`，B 进程使用 JDK21 的 `java.exe -jar`。实际运行时报告为 **21.0.2**，不是仅设置编译版本。原 `zj-market` 目录的未提交状态保持不变。

## 实际可运行组合

| 组件 | 本轮实际版本/方式 |
| --- | --- |
| B JDK | Oracle JDK 21.0.2，`C:/Program Files/Java/jdk-21`；B 字节码 major65 |
| B Spring Boot / Spring Framework | 4.1.1 / 7.0.9 |
| B Web 容器 | Tomcat 11.0.24；真实 Web 服务启动，回环地址、随机端口 |
| A 运行时 | 现有 Java8、Boot2.7.12 打包产物；临时隔离 Provider |
| A/B 契约 | v2基线1.1；`cn.bugstack:group-buy-market-contract:1.0-SNAPSHOT`；契约字节码 major52 |
| Dubbo | 原始 SDK 3.2.16；Triple直连，group=`gbm-dev`、version=`2.0.0`，TLS/mTLS |
| RocketMQ SDK / ACL / Broker | 4.9.7 / 4.9.7 / 现有 Docker Broker4.9.7 |
| Netty | 4.1.118.Final；最终打包核心模块保持同一版本 |
| A 契约 JSON 编解码 | Jackson2 databind/core 2.21.5、annotations2.21；独立 canonical mapper |
| B HTTP JSON | 保留 Boot 的 Jackson3 databind/core 3.1.5；没有替换 HTTP mapper |
| 日志 API | Boot 管理的 SLF4J2.0.18；实际启动和 SDK 调用通过 |

A/B 对应契约 JAR（A 可执行包内、A target 和 B 所用 Maven 缓存）的 SHA-256 一致：

`EEB3E9EC8D73E4C4CED28A86104004AD43CC075B793C2149D7625248FD0604DB`

首次环境验证的 B JAR SHA-256（历史产物，后续重新构建会变化）：

`93E3A1F06A8652C705A5D6FAC582CD9D6FB19A2482BF3BBFA8ACC83F8EF65B20`

A 实际运行 JAR SHA-256：

`223A02521120F6D83CB58220E7CFF08839A5B6BCBAC9BC5C00BCA42F8E6C8392`

## 默认组合与对照结果

| 实验 | 实际结果 |
| --- | --- |
| 原有 B、不引入 SDK | JDK21 构建及原有启动测试通过 |
| 引入 SDK，Boot 默认 Netty4.2.17 | B 启动成功；TLS查询阶段失败，RpcException；A 记录 `SSLHandshakeException: Received fatal alert: certificate_unknown` |
| 仅覆盖 Netty4.1.118 | RPC查询、认证负向、MQ往返、持久结果查询、Broker权限负向全部通过 |
| 同一证书重新对照 Netty4.2.17 | 再次在TLS查询阶段失败，未进入MQ步骤 |
| 最终POM固定4.1.118、不带覆盖参数 | 全部最小链路通过，进程退出码0 |

这是该 JDK/SDK/证书配置下的兼容性证据，不宣称所有 Netty4.2 配置均不可用。没有以关闭 TLS 或跳过证书校验来换取通过；后续升级 SDK/Netty 时重新验证该链路。

## 已执行的验收

- 实际 B 进程 PID **42084**，2026-10-03 **17:42:44（Asia/Shanghai）**启动；运行时报告 JDK21.0.2、Boot4.1.1、Netty4.1.118。
- 签名调用现有 `IntegrationService.queryEventResult`，随机不存在事件返回 `NOT_FOUND`，requestId 完整往返。
- 无效 RPC 签名返回 `AUTH_INVALID`，没有执行成功。
- B 使用既有 B Broker 凭据发布签名 `PRODUCT_SNAPSHOT_CHANGED` 至 `B_PRODUCT_EVENTS-dev`，发送确认 `SEND_OK`。
- 实际 B 通过授权组 `B_INTEGRATION_RESULTS-dev` 接收 A 的 `EVENT_PROCESSING_RESULT`；核验 Topic、Tag、消息键、来源渠道、A producer、keyId 和原始正文 HMAC。
- 反序列化处理结果为 `APPLIED/0000`；核对原事件关联、商品ID、版本字符串、applied布尔值与售卖状态。
- 再次调用查询接口返回 `0000`，数据为 `PROCESSED/APPLIED`，确认 A 已持久处理，不能只用 Broker SEND_OK 代替业务完成。
- B 向 A 专属 `A_TEAM_EVENTS-dev` 发布，被 Broker 明确以权限错误拒绝；连接超时不算 ACL 通过。
- Maven测试 **3/3**，无失败、错误或跳过：原有 B 启动测试；A 公开 Unicode/null/规范JSON/SHA256/HMAC 向量；MQ正文或Topic被修改时签名失效。
- 检查 verbose 依赖树与可执行 JAR 的实际库列表：Spring Framework 7.0.9 保留，Dubbo 请求的旧 Spring 版本由 Boot 管理；Netty 核心模块统一4.1.118，没有4.2混装。未引入 A 的 Boot2 Starter。
- 所有自建临时 Java 进程结束，50051/18091 监听已释放。已有开发容器保留运行。

最终事件ID：`b01-0d43aee7-98d1-47b0-9f77-c65fde8f5ed8`。
隔离商品ID：`b01-0811b788-db3d-4177-a38d-ee6f0812e7b2`。

## 复现入口与证据

在 B 工作树根目录运行：

```powershell
./docs/tests/run-b01-environment.ps1
```

脚本显式选择 JDK21构建/启动 B，使用已有 A JAR、开发凭据和容器；只启动连接 `group_buy_market_phase1_test` 的临时 A，不执行迁移。测试证书由现有 JDK 生成，凭据从 A 被忽略的 `.local/app.env`、`b.env` 注入，不复制到 B 源码或文档。外部路径可用 JavaHome、AJavaHome、AProject 参数指定。

需要已有13306/16379/9876/10911服务、空闲50051/18091端口，以及可读取的 Maven 仓库。该验证组需要独占使用，不要与另一个 B 消费者同时运行。本轮仅在隔离库保留唯一测试商品及消息处理审计记录，没有创建商城交易、支付或退款。

受控版本对照命令（NettyVersion 是实验参数，常规运行无需使用）：

```powershell
./docs/tests/run-b01-environment.ps1 -RunName netty42-control -NettyVersion 4.2.17.Final -TlsDirectory target/environment-probe/netty41-candidate/tls
```

证据均在被Git忽略的 `target/environment-probe/`：

- `baseline-build.log`、`baseline-dependencies.txt`：原工程基线。
- `sdk-default/report.json`：默认Netty失败。
- `netty41-candidate/report.json`、`netty42-control/report.json`：对照结果。
- `verified/build.log`、`verified/dependencies.txt`、`verified/report.json`：最终POM验证。
- `verified/a.stdout.log`、`verified/b.stdout.log`：实际进程日志。
- `packaged-libraries.txt`：最终可执行包依赖列表。

验证入口仅在 `environment-probe` profile 或显式属性启用时运行；默认启动不连接 A/MQ。此入口是有界测试工具，接收结果仅作内存断言，**不是生产 Inbox、Outbox 或业务消费者**。

## 未覆盖范围与下一步

Broker 仍采用既有回环明文开发例外，**Broker TLS 未验证**；Triple 使用本地临时测试证书，不代表正式证书部署或跨主机网络已验收。本轮也不代表全部RPC方法、完整消息类型、库存/支付/退款/履约及故障恢复通过。

本次完成用户要求的“先验证实际 B 运行环境”。后续在已验证的组合上继续 B-01 的工程分层、配置边界和独立数据库设计；不将 B-01 整体标成已验收。

## 本次任务实施复杂度

**中等。** 需要在实际B进程中协调JDK、Boot、SDK、Netty、两代Jackson、TLS认证与MQ ACL，主要难点是通过受控对照区分“启动成功”和“实际互通成功”。已按基线构建 → TLS/RPC查询 → MQ授权往返 → 最终依赖固定与复验四步实施；没有扩展为完整商城业务。

## 统一启动入口复验与本次复杂度

2026-10-03：继续保留上述版本及编解码，通过[统一启动说明](b-startup.md)集中B的JDK21选择。既有RPC/MQ脚本用统一入口复验通过（unified-entry/report.json，PID23856），3项测试通过，成功/失败后终端环境恢复为原Java8。A子进程单独选择Java8。新增Docker21模板但未运行容器，IDE仅检查配置。此次实施复杂度低，主要是确认和复用，没有重新选型或扩展业务。

## DDD拆分后的当前入口与本次复杂度

2026-10-03：现有源码迁移至六模块，ContractCodec归基础设施，EnvironmentProbe及其profile仅在verification中。普通app exec JAR不含验收入口；独立验收复用真实B引导和配置并完成RPC/MQ复验（ddd-final/report.json，PID53140）。本报告之前的根target产物路径、3项测试和指纹属于历史单模块证据；当前产物、8项测试及配置边界以[模块记录](phase1-architecture.md)为准。此次实施复杂度中等，因需协调依赖、双入口和配置/凭据隔离，没有升级既有框架或SDK。

## 2026-10-10历史状态校正复杂度

此次文档维护复杂度低：依据Git归档修正当前入口并明确历史实施范围，保留原验收批次、路径和指纹；未改变业务规则或重新执行业务验收。后续详细过程维护于 [B-04开发过程](b04-development.md)，总体进度同步[路线图](development-roadmap.md)。
