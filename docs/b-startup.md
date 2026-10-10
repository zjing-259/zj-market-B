# B 的统一启动方式

更新：2026-10-09。当前目录优化工作树：`D:/Java/zj-market-b02-noFileUpdate`，分支：`b02-noFileUpdate`。下文旧验收日期记录保留为历史证据。

## 固定基线

继续使用JDK21、Spring Boot4.1.1、Netty4.1.118.Final、Dubbo3.2.16、RocketMQ4.9.7及独立Jackson2签名编解码；HTTP保持Jackson3。版本证据见[环境验证](phase1-environment.md)，当前七模块和配置边界见[文件规范](project-layout.md)；[B-01拆分记录](phase1-architecture.md)为历史六模块基线。

本机JDK为 `C:/Program Files/Java/jdk-21`（Oracle21.0.2）。B脚本共用scripts/b-runtime.ps1：-JavaHome参数优先，其次B_JAVA_HOME，最后使用已验证路径。只临时改变进程环境，退出后恢复JAVA_HOME/PATH；终端和A仍使用Java8。

根POM是聚合POM。普通运行产物在 `zj-market-app/target/zj-market-app-exec.jar`，验收产物在 `zj-market-verification/target/zj-market-verification.jar`；旧根target单模块JAR不再由脚本启动。

## Maven与普通启动

```powershell
./scripts/mvn.ps1 --version
./scripts/mvn.ps1 package
./scripts/start-b.ps1
./scripts/start-b.ps1 -SkipBuild
./scripts/start-b.ps1 -SkipBuild -ApplicationArguments @('--server.port=8081')
```

mvn.ps1使用已有Maven3.8.8并选择JDK21；package构建全部模块。start-b.ps1默认只构建app和依赖，然后启动普通exec JAR；不会构建或运行verification。不修改原生mvnw；直接在Java8终端运行Maven生命周期，会被POM的JDK21约束拒绝。

不设置集成enabled开关时，普通启动不需要RPC/MQ/数据库凭据。要接入外部资源时，使用B_RPC_*、B_MQ_*、B_DATABASE_*或外部Spring配置；具体字段及启用条件见DDD拆分记录。

## IDEA

打开根pom.xml并重新导入，使用 `B - JDK 21` 共享配置；模块为zj-market-app，主类cn.zj.zjmarket.ZjMarketApplication。项目SDK、语言级别、Maven Runner和Importer本地配置继续为21。.idea保持忽略，共享.run配置可纳入版本控制。

其他机器需将SDK名21映射到实际JDK21安装。IDE项目/Maven JDK分别配置，[JetBrains文档](https://www.jetbrains.com/help/idea/maven-support.html)有对应设置。本轮只检查文件配置，没有通过IDE界面实际启动。

## 独立A/B验收

```powershell
./docs/tests/run-b01-environment.ps1
./docs/tests/run-b01-environment.ps1 -RunName ddd-final -SkipBuild
```

该脚本构建并启动verification产物，其引导复用普通B的ZjMarketApplication及基础设施，加上本机验收Runner。验收profile及明文回环MQ例外只位于verification模块，普通包没有该入口。

A Provider使用独立AJavaHome（Java8）；B使用JDK21；B进程不继承A的SPRING_DATASOURCE_*凭据。凭据仅从已有被忽略的开发环境文件注入，测试证书及日志在被忽略的target目录。各模块依赖树存于各自target/environment-probe/dependencies.txt。

## 后续Docker

Dockerfile使用eclipse-temurin:21-jdk，只复制普通app exec JAR；.dockerignore不包含verification或证书/凭据。

```powershell
./scripts/mvn.ps1 -pl zj-market-app -am package
docker build -t zj-market:b01 .
docker run --rm -p 8080:8080 zj-market:b01
```

本轮没有构建或启动B容器；统一的是JDK主版本21，镜像厂商/补丁不等同已验证Oracle21.0.2。容器RPC/MQ地址、正式证书和Broker TLS仍需独立验证。

## B-01验证（历史基线）

模块构建及8项测试通过；普通Web启动通过；普通包物理排除验收模块，显式传验收profile/开关也不运行探针；独立验收RPC/MQ往返通过。终端Java8保持不变，详情及产物指纹见DDD拆分记录。此前单模块启动验证保留在环境报告作为历史证据。

## 本次任务实施复杂度

**中等。** 本次模块拆分同时更新了依赖、配置、两个启动产物和脚本/IDE/Docker路径，复用固定JDK和版本组合；8项边界/编解码/引导测试及真实RPC/MQ验收通过。没有扩展业务或执行数据库迁移。

## 独立数据库启动增量

本地运行数据库已建立；普通启动显式选择加密凭据文件时只注入运行账号。实际用法：

```powershell
./scripts/start-b.ps1 -DatabaseCredentialFile ./.local/database.credentials.xml
./scripts/database.ps1 -Mode migrate
./scripts/database.ps1 -Mode verify
```

普通启动不执行迁移，未选择凭据时仍默认禁用数据库；外部B_DATABASE_*也可使用。数据库/迁移角色、生产限制与完整验收见[数据库记录](phase1-database.md)。

此次增量复杂度中等：增加数据库账号与显式迁移，保持普通/验收入口及JDK21一致；实际数据库验收和环境恢复通过，未新增交易表。

## B-02商品启动增量

商品HTTP和页面使用scripts/start-products.ps1，显式开启商品/身份/数据库，实际JDK仍由b-runtime.ps1选择21；start-identity.ps1继续为仅身份入口。事件producer/source/channel与JWT公私钥、origin、数据库运行凭据均外部注入，未配置有效事件归属会拒绝启动，不要求A RPC或MQ客户端在线。普通启动不执行迁移。

完整配置、开发/测试库边界、复现命令与B-02.3状态只维护在当前分支[B-02过程文档第12节](b02-development.md)。一键商品HTTP与浏览器验收入口为docs/tests/run-b02-products.ps1、run-b02-products-browser.ps1；使用独立B测试库并只停止自己启动的进程。B-02.3已完成实际验收；D12按用户选择沿用A的128个UTF-16单元上限，名称边界复验通过。

此次B-02.3实施复杂度高，按权威过程文档第12.1节的领域/持久化、事务/HTTP、页面、综合复验四步推进；此启动索引增量复杂度低，复用既有JDK21和凭据边界。

## B-02可靠同步启动增量

完整商品同步使用scripts/start-sync.ps1，显式开启身份、商品、RPC/MQ和后台恢复，并复用同一JDK21、外部运行凭据和已有签名编解码。start-identity.ps1和start-products.ps1显式关闭同步及RPC/MQ，防止继承外部变量导致单独入口意外启用集成。普通包不迁移，启动前由database.ps1显式完成V4；普通B不继承迁移账号及仅用于隔离验收的A Broker凭据。

正式消费者使用独立业务组，最多重新消费8次。运行参数、运营页面、受控隔离维护及完整复现命令统一维护在当前分支[B-02过程文档第13节](b02-development.md)；联合验收入口为docs/tests/run-b02-sync.ps1 -Browser，维护入口为scripts/sync.ps1 -QuarantineId，均显式JDK21，凭据外部注入。

此次启动索引复杂度低，可靠同步实现复杂度高；权威过程文档分四步记录依赖、验收与实际边界，本文件不另建B-02过程记录。

## B-02商城试算启动增量

完整商城使用scripts/start-market.ps1，显式开启身份、商品、可靠同步、RPC/MQ及优惠试算，继续由已有脚本选择JDK21。start-identity.ps1、start-products.ps1、start-sync.ps1分别保留单独入口并显式关闭试算；普通B启动不迁移，运行凭据、JWT公私钥、RPC/MQ签名与TLS配置全部外部注入，不继承验收账号密码。

实际A试算与正常B商城页面的完整复现入口是docs/tests/run-b02-trial.ps1 -Browser。它仅使用独立B测试库和已有A隔离库，保持A使用JDK8，不改终端默认Java8。当前阶段的用户选择、边界、复现与证据只维护在当前分支[B-02过程文档第14节](b02-development.md)；本文件仅索引启动入口。

此次索引复杂度低；B-02.5实际实现复杂度高，依赖身份、当前商品版本和可靠同步，第14节分四步实施与验收。B-02.6尚未开展。

## B-02联合验收及交接入口

B-02闭环已通过B-02.6联合验收。统一复现使用docs/tests/run-b02-acceptance.ps1，顺序构建、验证双B库迁移/权限、同步及消费提交后ACK前跨进程恢复、身份商品及正常在线/离线商城、原RPC/MQ/签名基线；总报告、子报告位置、产物SHA256及环境恢复在target/acceptance/<RunName>/report.json。默认包含真实浏览器，不以模拟页面代替验收。

运行前保持已有本地学习服务、A包及独立库/外部凭据可用，使用新的RunName，不停止无关进程。正常完整商城仍scripts/start-market.ps1，迁移仍scripts/database.ps1；完整阶段记录唯一在原目录[B-02过程文档第15节](b02-development.md)，B-03字段交接及后续范围见第15.3节。B-03尚未开展。

此次启动索引复杂度低；B-02.6联合验收与交接中等复杂度，三步依赖及实际证据均已记录。

## B-02目录优化后的启动确认（2026-10-09）

当前七模块布局、Java包与前端归位已完成，普通main/JAR、脚本和JDK21选择保持。IDE加载此工作树根pom.xml后重新导入Maven，旧application模块应消失；运行模块仍app、主类仍cn.zj.zjmarket.ZjMarketApplication。图形IDE本轮未实际启动，脚本普通应用、HTTP/浏览器和独立验收均通过，实际批次 `layout-20261009-110821` 及复现命令见 [B-02第17节](b02-development.md#17-b-02文件管理优化2026-10-09)。本轮15项测试、正常包排除verification/Flyway，默认Java8和调用方环境恢复已确认；B容器仍未执行验收。


## B-03.2库存启动增量（2026-10-09）

完整商城scripts/start-market.ps1现显式开启库存b.inventory.enabled，继续使用JDK21及已有外部数据库/JWT/RPC/MQ配置。先执行V5库存基础和V6请求审计迁移，再给运行账号三张库存表DML权限；普通启动不自动迁移，不使用迁移账号运行。已执行迁移不改写，旧版商品写入口不得在迁移后继续创建漏账户商品。

仅本地身份/商品/库存开发可先外部设置B_INVENTORY_ENABLED=true，再运行scripts/start-products.ps1；该入口仍关闭真实RPC/MQ/试算。浏览器运营入口为/admin/inventory。身份/数据库维护CLI显式关闭库存，防止继承功能开关。准确余额和流水只对运营开放，公开商品只有有货/缺货。

验收入口docs/tests/run-b03-inventory.ps1和run-b03-inventory-browser.ps1，均显式选JDK21、限定现有独立B测试库；凭据/密钥仍在外部或被忽略.local，浏览器恢复信息只存业务参数，不存登录凭据。完整过程、命令、证据及范围见[B-03第14节](b03-development.md#14-b-032实现与验收2026-10-09已完成)。

## B-03.3本地订单启动增量

完整商城start-market.ps1显式启用b.order.enabled，需先在受控窗口执行V7并授予新增五表DML（运行账号共19张B表），真实A试算/RPC配置仍由外部注入。B_ORDER_ENABLED默认false；维护CLI显式关闭订单。start-products.ps1仍用于不连接A的商品/库存页面，不自动开启订单。

/orders提供本人订单列表/详情，商品详情先核对报价再确认购买。本阶段订单先进入PROCESSING并持久预留，worker发送A reserve在B-03.4，取消和超时释放在B-03.5；当前不开放支付或取消按钮，页面倒计时不触发释放。运行B-03.3本地验收用docs/tests/run-b03-orders.ps1；真实A联调用run-b03-readiness.ps1 -WithLocalOrders及新RunName；浏览器验收专用入口绝不作为普通商城启动。

## B-03.4 A占位与结果恢复启动增量

完整商城start-market.ps1显式启用b.trade.enabled，先在无旧B写进程的受控窗口执行V8并授予b_trade_attempt DML（运行账号共20张B表）。普通启动不迁移；沿用JDK21、既有签名编解码/Netty及外部RPC/TLS/账号配置。单独identity/products/sync脚本、维护CLI及非交易验收显式关闭trade/order，防止继承开关触发后台占位。

后台默认扫描2秒/20条、逐条租约30秒、RPC10秒；B_TRADE_SCAN_MILLIS/B_TRADE_BATCH_SIZE/B_TRADE_LEASE_MILLIS与B_TRADE_RETRY_BASE_MILLIS/B_TRADE_RETRY_MAX_MILLIS可外部配置。退避默认2/4/8/16/30秒加抖动并限于30秒；5次技术失败记录告警并继续恢复。关闭调度可用B_TRADE_SCHEDULER_ENABLED=false，保留持久任务，不用重建订单恢复。

/teams/{teamId}登录后展示安全团队摘要及分享地址，指定团队参团不自动改成开团；/orders显示已验证A团队/期限和核对状态。支付仍未接入，取消/关闭执行与HELD释放按B-03.5实施。复现与真实A/进程重启/MySQL/页面证据集中维护在[B-03过程第16节](b03-development.md#16-b-034-a占位与结果恢复2026-10-09已完成)。

本次启动索引复杂度低，复用既有入口；交易恢复实施复杂度高，分步依赖和验收以过程文档为准。

## B-03.5未支付关闭入口

完整商城沿用start-market.ps1与显式JDK21。在无旧B写进程的受控窗口执行新增V9并为b_order_operation授予DML，运行账号共21张B表；普通启动仍不自动迁移，凭据/私钥外部注入。已执行V1～V8不改写，框架/Netty/签名方案不变。

/orders/{orderId}提供本人未支付取消、关闭进度与关闭依据；/admin/orders及/admin/orders/{orderId}提供运营异常和允许的任务控制。鉴权故障CHECK仅原单只读签名查询，可信后恢复；证据矛盾不能页面强制恢复。可能已发时确认A关闭后才释放，支付仍未开放。

独立验收用docs/tests/run-b03-closes.ps1，真实A/进程重启用run-b03-readiness.ps1 -WithUnpaidClose，浏览器用run-b03-orders-browser.ps1 -WithClose；均显式传入-JavaHome 'C:/Program Files/Java/jdk-21'。复现及证据见[B-03过程第17节](b03-development.md#17-b-035-未支付关闭与页面闭环2026-10-09已完成)。索引更新复杂度低，实际关闭实现复杂度高并按过程文档分步验收。

## B-03.6联合故障验收入口

从b03工作树运行（PowerShell7，外部/DPAPI凭据，不把密码写入命令或仓库）：

```powershell
pwsh -NoProfile -File docs/tests/run-b03-acceptance.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -RunName <新的唯一批次>
```

默认重新打包并执行单元测试，随后同一产物验证普通JDK21启动、双库V9/权限、完整B-02回归、库存/订单/交易/关闭及组合故障、真实A离线重启/B新进程恢复和Edge页面。每批target/b03-acceptance/<批次>独立保存报告、产物指纹及本批证据，拒绝覆盖旧批次或引用旧通过报告。SkipBuild表示本次没有重新执行单元构建，不能当作新测试证据。

用户确认的历史同步积压隔离仅用于验收：统一入口传ScopedSyncBrowser，逐层选择verification包--sync-browser，只认领本次browser-fixture.json事件；试算页面同开关选择verification的--trial-browser，本批本地allowlist只登记页面实际修改/恢复返回的eventId和goodsId，后台核对关联/正文哈希。两者复用真实同步服务、A和MQ。正常ProductSyncJob不变，旧数据保留；生产不使用scripts/start-sync-verification-browser.ps1或start-trial-verification-browser.ps1，不把验收入口作为常规启动。未传开关时B-02验收仍沿用原全局后台。

单独组合故障用docs/tests/run-b03-joint-faults.ps1；真实A停启及B进程恢复用run-b03-readiness.ps1 -WithJointFaults，均显式JavaHome且使用新的RunName（后者）。只停止本次启动的A/B/Vite/浏览器进程，共享MySQL/MQ保持；启动前要求专用端口空闲，结束检查环境、端口及终端默认Java8。完整结果见[B-03过程第18节](b03-development.md#18-b-036-联合故障验收与交接2026-10-09已完成)，资金接续见[b03-payment-handoff.md](b03-payment-handoff.md)。

索引维护复杂度低；联合验收复杂度高，按组合竞争→同批指纹→真实故障/页面→守恒→交接→安全六步执行。真实支付/退款留后续阶段。

## B-03收尾：D6可配置等待期限（2026-10-10）

`B_ORDER_RESERVE_WAIT_MILLIS`对应`b.order.reserve-wait-millis`，单位毫秒，默认300000（5分钟）；也可通过Spring启动参数覆盖。开启订单模块时必须为正的long整数，零/负数及不能解析为long的值拒绝启动。计算数据库绝对期限使用Math.addExact，溢出不提交订单。

```powershell
$env:B_ORDER_RESERVE_WAIT_MILLIS='60000'
./scripts/start-market.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -TestDatabase -SkipBuild
```

该配置仅用于新订单，从数据库创建时刻计算并持久化reserve_wait_deadline_ms。已受理订单和原键重试继续使用原期限，不按当前配置续期；D9报价确认仍独立5分钟，A付款截止不受影响。到期持久关闭，严格未发才本地释放；可能已发仍须确认A关闭。普通IDE、Maven、脚本均通过同一Spring配置读取。演示结束应恢复原环境变量；真实凭据与密钥仍外部注入。

收尾复杂度中等：配置注入与参数保护→默认/自定义/原键/D9回归→真实数据库与关闭验证→阶段当前状态与历史归档统一。证据见B-03过程第19节。
