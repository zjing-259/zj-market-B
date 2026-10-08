# B 的统一启动方式

更新：2026-10-03。工作树：`D:/Java/zj-market-b01`，分支：`codex/b-01`。

## 固定基线

继续使用JDK21、Spring Boot4.1.1、Netty4.1.118.Final、Dubbo3.2.16、RocketMQ4.9.7及独立Jackson2签名编解码；HTTP保持Jackson3。版本证据见[环境验证](phase1-environment.md)，当前模块和配置边界见[DDD拆分记录](phase1-architecture.md)。

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

## 当前验证

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

完整配置、开发/测试库边界、复现命令与B-02.3状态只维护在原目录[B-02过程文档第12节](D:/Java/zj-market/docs/b02-development.md:285)。一键商品HTTP与浏览器验收入口为docs/tests/run-b02-products.ps1、run-b02-products-browser.ps1；使用独立B测试库并只停止自己启动的进程。B-02.3已完成实际验收；D12按用户选择沿用A的128个UTF-16单元上限，名称边界复验通过。

此次B-02.3实施复杂度高，按权威过程文档第12.1节的领域/持久化、事务/HTTP、页面、综合复验四步推进；此启动索引增量复杂度低，复用既有JDK21和凭据边界。

## B-02可靠同步启动增量

完整商品同步使用scripts/start-sync.ps1，显式开启身份、商品、RPC/MQ和后台恢复，并复用同一JDK21、外部运行凭据和已有签名编解码。start-identity.ps1和start-products.ps1显式关闭同步及RPC/MQ，防止继承外部变量导致单独入口意外启用集成。普通包不迁移，启动前由database.ps1显式完成V4；普通B不继承迁移账号及仅用于隔离验收的A Broker凭据。

正式消费者使用独立业务组，最多重新消费8次。运行参数、运营页面、受控隔离维护及完整复现命令统一维护在原目录[B-02过程文档第13节](D:/Java/zj-market/docs/b02-development.md:362)；联合验收入口为docs/tests/run-b02-sync.ps1 -Browser，维护入口为scripts/sync.ps1 -QuarantineId，均显式JDK21，凭据外部注入。

此次启动索引复杂度低，可靠同步实现复杂度高；权威过程文档分四步记录依赖、验收与实际边界，本文件不另建B-02过程记录。

## B-02商城试算启动增量

完整商城使用scripts/start-market.ps1，显式开启身份、商品、可靠同步、RPC/MQ及优惠试算，继续由已有脚本选择JDK21。start-identity.ps1、start-products.ps1、start-sync.ps1分别保留单独入口并显式关闭试算；普通B启动不迁移，运行凭据、JWT公私钥、RPC/MQ签名与TLS配置全部外部注入，不继承验收账号密码。

实际A试算与正常B商城页面的完整复现入口是docs/tests/run-b02-trial.ps1 -Browser。它仅使用独立B测试库和已有A隔离库，保持A使用JDK8，不改终端默认Java8。当前阶段的用户选择、边界、复现与证据只维护在原目录[B-02过程文档第14节](D:/Java/zj-market/docs/b02-development.md)；本文件仅索引启动入口。

此次索引复杂度低；B-02.5实际实现复杂度高，依赖身份、当前商品版本和可靠同步，第14节分四步实施与验收。B-02.6尚未开展。

## B-02联合验收及交接入口

B-02闭环已通过B-02.6联合验收。统一复现使用docs/tests/run-b02-acceptance.ps1，顺序构建、验证双B库迁移/权限、同步及消费提交后ACK前跨进程恢复、身份商品及正常在线/离线商城、原RPC/MQ/签名基线；总报告、子报告位置、产物SHA256及环境恢复在target/acceptance/<RunName>/report.json。默认包含真实浏览器，不以模拟页面代替验收。

运行前保持已有本地学习服务、A包及独立库/外部凭据可用，使用新的RunName，不停止无关进程。正常完整商城仍scripts/start-market.ps1，迁移仍scripts/database.ps1；完整阶段记录唯一在原目录[B-02过程文档第15节](D:/Java/zj-market/docs/b02-development.md)，B-03字段交接及后续范围见第15.3节。B-03尚未开展。

此次启动索引复杂度低；B-02.6联合验收与交接中等复杂度，三步依赖及实际证据均已记录。
