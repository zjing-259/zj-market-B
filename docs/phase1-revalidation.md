# 重构后的实际 B 复验

日期：2026-10-03（北京时间21:04～21:08）。工作树D:/Java/zj-market-b01，分支codex/b-01。
状态：此次重新打包、普通启动、已有RPC/MQ/签名和数据库访问复验全部通过。本轮没有修改业务代码或依赖版本，B-01整体仍为开发中。

## 构建与实际启动

清理六个子模块后重新执行package，使用C:/Program Files/Java/jdk-21（实际21.0.2）。
只清理模块target，保留根target内的历史验收证据；本轮证据独立存放于target/revalidation/refactor-20261003-210409。

| 检查 | 实际结果 |
| --- | --- |
| 六模块clean/package | 全部SUCCESS |
| 配置边界测试 | 5项通过 |
| 独立签名编解码测试 | 2项通过，包含A规范向量和签名篡改拒绝 |
| 普通引导隔离测试 | 1项通过 |
| 普通启动脚本+运行数据库凭据 | app exec JAR、JDK21启动成功，PID80884 |
| 普通Web启动+运行数据库凭据 | app exec JAR、JDK21启动成功，PID79944，本地18092响应404 |
| 产物隔离 | 普通包没有verification、Flyway或验收profile |

根路径404符合目前尚未实现首页路由的状态，仅证明Web服务和请求处理正常，不代表商城页面完成。
普通Web进程加载了真实运行账号配置；实际SQL连接及操作由以下数据库验收使用同一B引导与Hikari完成，不能把Web启动日志本身当作SQL成功证据。

## RPC / MQ / 签名真实复验

重新打包后运行已有docs/tests/run-b01-environment.ps1，RunName=refactor-20261003-210409，-SkipBuild确保使用此次产物。
A沿用Java8与独立group_buy_market_phase1_test测试库；B使用JDK21和Triple TLS。验收B进程PID79032。

| 检查 | 结果 |
| --- | --- |
| 带有效签名的queryEventResult | NOT_FOUND（随机新事件的预期结果） |
| 非法RPC签名 | AUTH_INVALID |
| MQ发布授权商品事件 | SEND_OK |
| MQ结果订阅授权 | AUTHORIZED |
| A结果消息签名验证及事件确认 | VERIFIED_APPLIED |
| RPC查询持久化结果 | PROCESSED_APPLIED |
| 发布A_TEAM_EVENTS | PERMISSION_DENIED |

本次eventId：b01-4d86cb35-7320-4679-8a56-f822665c3734。
本次goodsId：b01-9a8c9849-1772-4bc4-9990-86a0adafc962。
已有脚本使用随机测试事件和商品执行真实链路；测试效果留在隔离的A测试环境，不清洗既有A数据。

报告确认实际组合仍为Boot4.1.1、Dubbo3.2.16、RocketMQ4.9.7、Netty4.1.118.Final、Jackson2.21.5与3.1.5，未调整框架。

## 数据库复验

重新打包后运行已有docs/tests/run-b01-database.ps1 -SkipBuild，完整入口通过。
真实B引导和Hikari连接zj_market，运行账号zj_market_app，迁移账号zj_market_migrator。

- 运行账号INSERT、UPDATE、SELECT、DELETE通过；事务回滚，无探针记录残留。
- 运行账号CREATE/ALTER/DROP及迁移历史读写被拒绝。
- 迁移账号在B内DDL/DML通过，临时表删除；全局建库被拒绝。
- 两类账号访问A正式/测试库、读取mysql.user及授权操作被拒绝，SHOW GRANTS边界检查通过。
- 错误密码得到MySQL1045、SQLState28000；误用A schema在配置阶段拒绝。
- Flyway12.4.0校验通过，本轮migrationsExecuted=0，没有重复应用V1。
- MySQL8.0.32、Hikari7.0.2、驱动9.7.0。只读核对B仅有b_database_probe、flyway_schema_history；探针行数0，历史只有成功的版本1。

权限与本地开发TLS/Host范围沿用[数据库说明](phase1-database.md)，没有提前设计订单、库存或支付表。

## 证据与恢复

| 位置（工作树根目录下） | 内容 |
| --- | --- |
| target/revalidation/refactor-20261003-210409/build.log | 清理构建、8项测试 |
| target/environment-probe/refactor-20261003-210409/report.json及A/B日志 | 真实RPC/MQ、运行版本与PID |
| target/revalidation/refactor-20261003-210409/rpc-mq.log | RPC/MQ入口执行记录 |
| target/revalidation/refactor-20261003-210409/database.log | 完整数据库验收 |
| target/revalidation/refactor-20261003-210409/database/ | 本轮数据库报告快照及schema-audit |
| target/revalidation/refactor-20261003-210409/web.json及web.stdout/stderr.log | 普通Web启动、HTTP、进程停止与环境恢复 |
| target/revalidation/refactor-20261003-210409/artifacts.json | 此次JAR的SHA256 |

普通app exec JAR SHA256：
7A88A47F0F974BD298C937A60D0C152A508949E9785AC33BF773B919DE474CB4

verification JAR SHA256：
D87D59A343D371A2841AFF5EA68B6B6668B66D40D623E0E0D167377EE0705B0A

本轮临时A/B进程均停止，50051/18091/18092监听已释放；既有开发容器保持运行。
数据库与Web脚本的环境恢复检查通过；RPC/MQ脚本执行原有finally恢复逻辑。终端默认java仍1.8.0_391，未修改用户/系统JAVA_HOME和PATH，未输出或提交凭据。

本次覆盖现有本机验收，不代表完整商城流程、生产数据库TLS、Broker TLS、跨主机环境或Docker部署已验收。

## 此次任务实施复杂度

低。本轮复用已有脚本和固定版本，重新构建后验证真实启动、链路、签名及数据库访问，没有新增业务设计；运行涉及多进程与环境恢复，已保留独立证据并检查清理结果。
