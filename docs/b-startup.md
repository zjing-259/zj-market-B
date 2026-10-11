> 最新Git归档状态（2026-10-11）：B-05.0～.6支持范围成果已提交为 `3de9404776377f778d5f6930d3c5ae6fd754bf68`，已快进合并master并原子推送；origin/b-05与origin/master已远程核验一致。当前分支b-05已关联origin/b-05。本条及过程归档记录随随后文档提交同步两分支；下文旧HEAD、未提交／未合并／未推送等保留各次实施时点，不代表最新状态。验收摘要中的基线和包指纹保持原始证据；B-06尚未实施。

> 当前状态（2026-10-11）：B-05.6联合故障验收与B-06交接已完成支持范围内验收。最终同包106项JUnit/前端构建、新SQL及跨JVM/浏览器、真实A无人/部分付款停机退款释放/全付款最后事件成团竞争、逐单资金库存及A名额只读核验、原三专项/交接审计/普通启动均通过。推荐D26～D28已写双路线图，证据及边界见[b05-development.md第15.2节](b05-development.md)、[B-06交接](b05-b06-handoff.md)与[持久验收摘要](tests/b05-joint-acceptance.json)。取消后异常收款正向自动资格未开放，隔离验收通过；此限制不宣称全自动闭环。b-05/53ad32d，全部成果未提交/合并/推送，B-06未开展。下文旧阶段状态保留历史时点。

> 当前状态（2026-10-11）：B-05.5库存收尾及运营页面已完成本阶段验收。双B库V18/runtime48表精确DML；最终同包106项JUnit、SQL05及跨JVM、实际B HTTP浏览器04、真实A live02停机退款/释放/新B重放/恢复后同步、原关单/结算/履约回归、只读交接审计及普通启动均通过。推荐D21～D25已写双路线图，详情见[b05-development.md第14.3节](b05-development.md)。最终只读归档target/refund/b055-20261011-delivery-03/report.json；.6完整联合故障矩阵未开展。b-05/53ad32d，全部阶段改动未提交/合并/推送。下文带日期的旧状态保留历史时点。

> 当前状态（2026-10-11）：B-05.4可信退款事实与A同步已实现并通过同包业务验收；b-05/53ad32d，阶段变更未提交/合并/推送。双B库V16/runtime46表精确DML；103项JUnit、SQL03/跨JVM、实际A live-02停启/签名MQ/严格查询/新B进程、关单/结算/履约回归及普通启动通过。推荐D18～D20已保存双路线图；最终归档见target/refund/b054-20261011-delivery-02/report.json，过程见[b05-development.md第13.2节](b05-development.md)。付费HELD/guard保留；库存释放/HTTP/页面归.5、完整联合矩阵归.6。A外部并行改动保持，实际验收A包及契约不变。下列旧状态保留历史时点。

> 当前状态（2026-10-11）：B-05.3独立模拟退款已完成并验收通过；b-05/53ad32d，全部阶段变更未提交/合并/推送。双B库V15、runtime46表精确DML；99项JUnit、同包SQL/跨JVM、真实A完整核对资格及自有A停止后独立退款、关单/结算/履约回归和普通包默认启动通过。新增推荐D15～D17已保存双路线图。最终报告target/refund/b053-20261011-delivery-02/report.json；详见[B-05过程12.2](b05-development.md)。退款MQ/库存释放/运营及页面归.4/.5，.4～.6未开展；下列旧状态保留历史时点。

B-05.3配置增量：b.refund.enabled/B_REFUND_ENABLED默认false（发现并接管新ELIGIBLE义务），recovery-enabled/B_REFUND_RECOVERY_ENABLED默认true，scheduler-enabled/B_REFUND_SCHEDULER_ENABLED默认true。依赖trade.events能力和V15；enabled或recovery-enabled任一为true才装配，scheduler=false停后台，enabled=false不会终止已承担任务。显式provision后再启，普通启动不迁移。scan-millis=2000、timeout-millis=10000、lease-millis=30000、renew-millis=20000、retry-base-millis=2000、retry-cap-millis=30000、jitter-millis=250，均可用对应B_REFUND_*环境变量覆盖；启动检查正值、timeout<lease、renew<lease等，5次失败告警仍恢复。无普通故障HTTP或用户退款结果按钮。真实验收工具可指定AProviderRpcPort/AProviderHttpPort（默认50051/18091，本轮50052/18092），基线工具和B TLS端点一同设置，清理只涉及自有进程/端口。具体复现见过程12.2。

> 当前状态（2026-10-11）：B-05.2到期完整核对已完成并验收通过；工作树D:/Java/zj-market-b-05，分支b-05/53ad32d，改动未提交/合并/推送。双B库V14、41表精确DML；87项JUnit、最终同包真实A成团竞争/部分付款丢响应跨JVM恢复、SQL及关单/结算/履约回归通过。最终报告target/reconciliation/b052-20261011-delivery-03/report.json；详见[B-05过程11.4](b05-development.md)。退款义务已持久化，资金仍NONE、付费HELD保留；退款执行归.3，.3～.6未开展。下列暂停及旧阶段记录保留历史时点，以本条和11.4为当前状态。

核对配置：b.reconciliation.enabled / B_RECONCILIATION_ENABLED=false控制发现新任务；recovery-enabled / B_RECONCILIATION_RECOVERY_ENABLED=true恢复既有任务；scheduler-enabled / B_RECONCILIATION_SCHEDULER_ENABLED=true控制调度。配置装配还要求b.trade.events-enabled=true及原订单/关闭/支付渠道、认证TLS RPC和V14 schema能力，普通默认启动不启外部能力。恢复不是新任务发现；checkout关闭不终止原任务恢复。显式provision迁移/授权后才启业务，普通包不迁移。固定2秒扫描/10秒A调用/30秒租约与有界退避已实现，退款参数化/续租未实现。验收入口run-b05-reconciliation.ps1、run-b03-readiness.ps1的WithReconciliation或WithReconciliationCompletion（各用新批次），最终collect-b05-reconciliation.py；参数及证据见过程11.4。

> B-04.6最新启动接续（2026-10-10）：.0～.6按模拟范围已完成，b-04/7cef241，全部成果未提交；双库V13/35表、77项JUnit及同包联合验收通过。唯一详细事实见[B-04过程第15节](b04-development.md)，B-05从[b04-b05-handoff.md](b04-b05-handoff.md)接完整核对/退款。普通写默认关闭，原资金/HELD/guard及待处理工作保留；B-05/B-06待开展。以下旧增量保留其阶段时点。

# B 的统一启动方式

> B-04最新增量（2026-10-10）：.5可信成团/库存确认/PENDING已完成，见[B-04过程第14节](b04-development.md)。当前双库V13、runtime35表DML；先显式provision迁移与授权，普通启动不迁移。成团后台随events及其scheduler恢复，checkout=false不阻断旧工作；本人待履约摘要随order装配，独立于消息/checkout写开关。普通资金写仍默认关闭，.6总验收待开展。以下按阶段的旧表数/状态保留历史时点。


> B-04当前增量（2026-10-10）：.3可信资金/消息见[B-04过程第12节](b04-development.md)；.4完整根关闭/竞争见[第13节](b04-development.md)。当前迁移V12、runtime34表DML；普通开关仍默认关闭，库存确认/待履约归.5。以下旧阶段配置/表数保留历史时点。

> 历史状态说明（2026-10-10）：本文保留各实施时点的工作树、分支、未提交/未合并/未推送状态、验收批次和产物指纹；这些记录不代表当前 Git 状态。B-02、目录整理与补修、B-03及D6收尾均已包含在 `7cef241`；当前接续工作树为 `D:/Java/zj-market-b-04`，分支 `b-04`。最新进度见 [B-04开发过程](b04-development.md)及[路线图](development-roadmap.md)。历史 `.local`、`target` 和前端依赖不随 Git 复制，旧报告不作为新工作树重新验收的证据。

更新：2026-10-10。当前工作树：`D:/Java/zj-market-b-04`，分支：`b-04`，接续提交 `7cef241`。B-01～B-03功能基线已归档；下文带阶段/日期的增量记录保留其当时范围和证据。普通入口仍为 `scripts/start-market.ps1`，B-04.2已实现模拟收银台/持久渠道基础，普通新写默认关闭；商城成功/可靠通知/已开放关闭证明/待履约继续按.3～.5推进。

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

B-03验收脚本可从当前工作树运行（PowerShell7）；先显式准备外部/DPAPI凭据及产物，再使用新的唯一批次，不把密码写入命令或仓库：

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

## 2026-10-10历史状态校正复杂度

此次文档维护复杂度低：依据Git归档修正当前入口并明确历史实施范围，保留原验收批次、路径和指纹；未改变业务规则或重新执行业务验收。后续详细过程维护于 [B-04开发过程](b04-development.md)，总体进度同步[路线图](development-roadmap.md)。


## B-04.0基线与接续（2026-10-10）

当前b-04工作树已独立构建并完成基线验证；实际配置复用、双库V9/权限、46项测试/前端、真实A/RPC/MQ及占位/关闭恢复、D6默认与自定义、样本/指纹/失败重跑及可重复命令见[B-04过程第9节](b04-development.md#9-b-040基线与接续2026-10-10已完成)。普通入口保持start-market.ps1，支付仍未实现；已有团队有期限且含直接A测试占位，未来资金验收须通过B建立新完整团队，不能将旧报告或已关闭B订单当待支付样本。


## B-04.3可信资金与可靠消息配置

先显式provision/migrate：当前V12，runtime34表。B_PAYMENT_ENABLED=true装配渠道/本人查询，B_PAYMENT_CHECKOUT_ENABLED=false只停新写；已有资金恢复需要B_TRADE_EVENTS_ENABLED=true及B_TRADE_EVENTS_SCHEDULER_ENABLED=true（后者默认true）。交易装配默认false，不受checkout关闭影响。配套身份/商品/库存/订单/trade及数据库/RPC/MQ均需开启并同clientId/source/channel；不开普通支付，不把.3单独启用当作完整资金闭环。

外部B_MQ_TRADE_TOPIC=B_TRADE_EVENTS-dev、B_MQ_TRADE_RESULT_GROUP=B_INTEGRATION_RESULTS-dev、B_MQ_TRADE_TEAM_GROUP=B_TEAM_EVENTS-dev；商品组保持B_PRODUCT_SYNC_RESULTS-dev，两组不得相同或使用PROBE组。本机现有ACL已授权这些业务组；跨机部署需单独核验自己的ACL，不能使用A凭据发B事实。HMAC/RPC/DB秘密继续外部注入，已有previous A keys轮换规则沿用。

隔离故障验证：docs/tests/run-b04-settlement.ps1；页面：run-b04-settlement-browser.ps1；真实通路：run-b03-readiness.ps1 -WithSettlement（隐含WithPayments/TradeRecovery/LocalOrders，须全新RunName，与旧未付关闭/联合故障模式互斥）。不重用未知资金样本或清除HELD/guard；所有操作保存独立target证据，普通包无verification/Flyway。


## B-04.4 支付开放后关闭配置

复用以上支付/资金装配，B_TRADE_EVENTS_ENABLED=true启用完整根关闭接续，B_TRADE_SCHEDULER_ENABLED=true运行原关闭扫描（默认true）；B_PAYMENT_CHECKOUT_ENABLED=false只停止新付款，旧订单取消与资金/关闭恢复继续。独立扫描无需新增开关；普通商城只提供原取消入口，不提供故障/资金强制成功/强制释放。先迁移V12，再启用装配；不要将不具备.5/.6的当前阶段作为普通环境完整支付闭环开放。

关闭隔离验证：run-b04-payment-closing.ps1；实际A：run-b03-readiness.ps1 -WithPaymentClosing。均指定JDK21和新的RunName；完整复现及证据见B-04过程第13节。原NEVER_OPENED回归仍由run-b03-closes.ps1验证。

## B-05.4 退款同步装配（2026-10-11）

先用verification迁移并校验V16；普通包无DDL/Flyway。启用B_TRADE_EVENTS_ENABLED=true且退款新接管或恢复任一启用时，RefundConfiguration校验V16并向原SettlementRepository装配退款同步。B_REFUND_ENABLED=false仅停新退款接管；B_REFUND_RECOVERY_ENABLED=true默认保留旧退款渠道恢复，B_REFUND_SCHEDULER_ENABLED控制该资金扫描。退款Outbox/Inbox复用B_TRADE_EVENTS_SCHEDULER_ENABLED和原SettlementJob，不另建MQ消费组；停止资金扫描不代表停止已承担的A同步。必须明确区分关闭全部trade events与仅关闭新接管。

退款网络发送/查询在订单事务外，调用前沿用原交易范围/TLS/HMAC；同步失败采用B_REFUND_RETRY_BASE_MILLIS/CAP_MILLIS/JITTER_MILLIS，默认2/4/8/16/30秒加0～250ms；正常发送确认后30秒查询结果。A的WAITING_DEPENDENCY/NOT_FOUND继续原事件恢复，ACK不记ACCEPTED。完整默认值仍见application.properties。.4不新增普通故障接口或退款HTTP。

隔离退款同步：run-b05-refund-sync.ps1；实际A停启及原事件/乱序/新B进程：run-b03-readiness.ps1 -WithRefundSync -AProviderRpcPort 50052 -AProviderHttpPort 18092（新b054批次）。沿用双库DPAPI凭据与JDK21，不停止50051上的外部A，不改A源配置。具体同包通过范围以过程13最终记录为准。

## B-05.5 启动与验收增量（2026-10-11）

先显式provision迁移双库至V18并授予48表精确DML，普通启动不迁移。本人/运营只读退款接口由b.order.enabled装配并验证V17读schema，独立于新退款接管；CHECK/RETRY还需RefundRepository恢复能力（含V18）。退款收尾恢复器由RefundConfiguration装配，沿用refund.scheduler-enabled，固定2秒扫描；scheduler=false停止其后台，验收仅显式处理本批原工作。既有新接管false/恢复true/普通外部能力默认关闭不变。CHECK仅查询原尝试并恢复原计划，不增加普通故障HTTP。

新增run-b05-refund-release.ps1、run-b05-refund-browser.ps1、run-b05-refund-release-regressions.ps1及collect-b05-refund-release.py；真实A入口run-b03-readiness.ps1 -WithRefundRelease（包含核对及退款同步），仅自有50052/18092。完整参数与同包证据见过程14.3～14.4。浏览器依赖Edge/Web Locks及仓库锁定Playwright；测试令牌仅忽略目录短期存在，用完删除，复跑新SQL批次。写库套件串行运行。

## B-05.6 联合验收与B-06接续（2026-10-11）

联合总入口docs/tests/run-b05-joint.ps1（新b056批次、JDK21）构建一次后串行七阶段，不运行全局旧任务批量清理。readiness新增-ReconciliationPaymentCase NONE用于无人付，默认PARTIAL保持；NONE禁止配退款执行/全付竞争，恢复原环境。额外collect-b05-quota.py只读管理员固定A隔离库本批团队，B运行权限不扩张；collect-b05-joint.py只读归档，通过才可--publish-summary。支持范围结果与完整参数见过程15.2～15.3；配置/迁移/开关不变，B-06交接见b05-b06-handoff.md。
