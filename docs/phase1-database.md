# B-01：独立数据库与访问边界

> B-04.3当前增量（2026-10-10）：见[B-04过程第12节](b04-development.md)。V11及34张B表DML、可信资金/独立交易消息、D6持久接管已完成验收；普通支付写与交易恢复装配默认关闭。开放后关闭证明/待履约归.4/.5；以下旧阶段配置/表数保留历史时点。

> 历史状态说明（2026-10-10）：本文保留各实施时点的工作树、分支、未提交/未合并/未推送状态、验收批次和产物指纹；这些记录不代表当前 Git 状态。B-02、目录整理与补修、B-03及D6收尾均已包含在 `7cef241`；当前接续工作树为 `D:/Java/zj-market-b-04`，分支 `b-04`。最新进度见 [B-04开发过程](b04-development.md)及[路线图](development-roadmap.md)。历史 `.local`、`target` 和前端依赖不随 Git 复制，旧报告不作为新工作树重新验收的证据。

更新：2026-10-03。工作树：D:/Java/zj-market-b01，分支codex/b-01。
状态：本地独立数据库、两类账号、显式迁移入口及真实连接/权限验收已完成。B-01整体仍在开发中。

## 实际运行配置

沿用现有开发MySQL容器mysql，Windows入口127.0.0.1:13306；建立独立数据库zj_market，字符集utf8mb4、排序规则utf8mb4_0900_ai_ci。
这是独立schema与账号，复用开发MySQL实例，不代表独立物理实例或生产部署完成。没有向A的group_buy_market或group_buy_market_phase1_test执行迁移。

| 项目 | 实际版本 |
| --- | --- |
| B JDK | 21.0.2 |
| Spring Boot | 4.1.1 |
| MySQL | 8.0.32 |
| HikariCP | 7.0.2 |
| MySQL Connector/J | 9.7.0 |
| Flyway | 12.4.0（沿用Boot依赖管理，仅verification依赖） |

固定Netty4.1.118及独立签名编解码保持不变；未升级或降级框架。B脚本仍显式选择JDK21，终端默认Java8。

## 账号与权限

| 账号 | 允许 | 拒绝及限制 |
| --- | --- | --- |
| zj_market_app | 仅zj_market.b_database_probe的SELECT/INSERT/UPDATE/DELETE | 无DDL、迁移历史权限、A库权限、系统库权限和GRANT OPTION |
| zj_market_migrator | 仅zj_market.*的SELECT/INSERT/UPDATE/DELETE/CREATE/ALTER/DROP/INDEX/REFERENCES | 无A库、全局建库、系统库读取和GRANT OPTION |

本机Docker桥接使用两个账号的Host=%；权限仍限制在上述B对象。现有MySQL端口绑定未由本轮修改。
本地连接URL显式sslMode=DISABLED及allowPublicKeyRetrieval=true，仅作为当前开发环境实测配置；生产连接的TLS、账号Host与网络边界需要在目标环境单独配置和验收。

不授权运行账号整个schema的DML，避免运行进程改写Flyway历史。后续增加业务表时，使用受控管理入口按具体表授予运行账号必要权限，迁移账号本身不能授予权限。本轮未提前设计订单、库存、支付表。

## 迁移与配置位置

- 数据源配置及Hikari工厂仍在infrastructure，使用B_DATABASE_*，不继承A的SPRING_DATASOURCE_*。
- SQL位于zj-market-infrastructure/src/main/resources/db/migration/V1__database_boundary.sql，仅建立b_database_probe基础设施表。
- 执行器DatabaseCommands位于verification；Flyway只存在于verification依赖。普通app包未包含Flyway或验收执行器。
- 显式迁移使用B_MIGRATION_USERNAME/B_MIGRATION_PASSWORD；运行连接使用B_DATABASE_USERNAME/B_DATABASE_PASSWORD，二者共享B_DATABASE_URL。
- 命令固定目标zj_market及本地B角色名；错误参数、错误账号或A schema在执行SQL前被拒绝。
- Flyway启用checksum校验、cleanDisabled=true、createSchemas=false、baselineOnMigrate=false；拒绝将未受控的非空库自动标记成基线。
- migrate会执行迁移、校验历史并检查迁移账号边界；其临时DDL检查表随后删除。verify使用真正的ZjMarketApplication引导和Hikari数据源，明确禁用RPC/MQ，检查运行账号权限。
- 普通启动不执行迁移，即使本地凭据存在也不会自动启用数据库。通过启动参数或外部B_DATABASE_ENABLED=true显式启用。

Flyway对默认schema和历史表位置的行为见[官方defaultSchema说明](https://documentation.red-gate.com/flyway/reference/configuration/flyway-namespace/flyway-default-schema-setting)；本实现默认schema=zj_market，历史表为flyway_schema_history。

## 外部凭据与操作入口

在工作树根目录执行：

```powershell
# 首次准备；使用现有开发容器内的管理员凭据，生成两份独立随机口令。
./scripts/provision-b-database.ps1

# 后续显式迁移或单独验证；已有构建可加-SkipBuild。
./scripts/database.ps1 -Mode migrate
./scripts/database.ps1 -Mode verify

# 普通启动只注入运行账号，不传递迁移账号，不执行迁移。
./scripts/start-b.ps1 -DatabaseCredentialFile ./.local/database.credentials.xml

# 完整数据库验收，覆盖负向场景与普通启动。
./docs/tests/run-b01-database.ps1 -SkipBuild
```

provision入口是当前本地Docker环境专用：管理员秘密仅在已有容器内使用，不复制A配置里的密码，不持久保存管理员凭据。
如发现已有B schema/账号却没有此工作树的凭据记录，脚本拒绝接管或覆盖。重复执行不修改现有账号口令、不删除数据库，也不重新应用已成功的V1。

B随机凭据存于被Git忽略的.local/database.credentials.xml，PSCredential经Windows DPAPI加密，只能由当前机器/用户解密。不要提交此文件。
database入口支持外部环境变量；设置B_DATABASE_URL时优先使用环境凭据，也可显式-CredentialFile指定加密文件。非Windows环境通过环境或外部秘密系统注入，不依赖本地加密文件。
普通启动脚本清除迁移凭据，迁移/运行验收各只向子进程传入对应角色的B数据库凭据；结束后恢复进程环境变量，不修改用户或系统设置。

## 实际验收证据

2026-10-03，本地JDK21下完成：

- 六模块构建成功，原8项配置/签名/普通引导测试全部通过。
- 首次迁移执行V1一次；重复执行migrationsExecuted=0且Flyway校验通过，历史只有版本1的一条成功记录。
- 实际B引导连接zj_market，运行账号INSERT、UPDATE、SELECT、DELETE全部成功，测试事务最终回滚。
- 运行账号CREATE、ALTER、DROP、读取及修改flyway_schema_history被拒绝。
- 迁移账号在B内CREATE、ALTER、INDEX及DML成功，临时表清除；创建库被拒绝。
- 两个账号USE A的正式/测试schema、读取mysql.user及GRANT均被拒绝；SHOW GRANTS确认没有额外对象或全局权限。
- 错误密码返回MySQL1045/SQLState28000；误用A schema在配置校验阶段拒绝。
- 普通app使用运行凭据启动成功；普通JAR中没有Flyway/verification依赖。脚本JDK/PATH及B凭据环境恢复通过。
- 只读核对B内只有b_database_probe、flyway_schema_history两张基础设施表；probe行数0，无交易数据或临时DDL表残留。

证据文件位于被忽略的target目录：

| 文件 | 内容 |
| --- | --- |
| target/database-build.log | 构建与8项测试 |
| target/database-provision.log、target/database/first-migrate.txt | 首次V1执行 |
| target/database/migrate.txt | 当前迁移版本/账号/权限检查及重复执行0条 |
| target/database/verify.txt | 真实B运行账号及CRUD/拒绝权限 |
| target/database/authentication-denied.txt | 无敏感文本的错误密码错误码 |
| target/database/a-schema-denied.txt | A schema配置拒绝 |
| target/database/normal-start.log | 普通app实际启动 |
| target/database-acceptance.log | 完整入口与环境恢复验收 |

此前真实RPC/MQ通过记录继续引用phase1-architecture.md与phase1-environment.md；本轮没有改动其协议或重新发送消息。生产TLS、跨主机权限、备份/恢复及业务表迁移不在本次验收范围内。

## 此次任务实施复杂度

中等。涉及真实建库与账号授权、独立迁移、凭据隔离和双向权限验证；按“检查冲突 → 建库/账号 → 基础迁移 → 真实连接/权限 → 幂等与错误场景”完成。不扩展订单、库存或支付模型。

## 2026-10-10历史状态校正复杂度

此次文档维护复杂度低：依据Git归档修正当前入口并明确历史实施范围，保留原验收批次、路径和指纹；未改变业务规则或重新执行业务验收。后续详细过程维护于 [B-04开发过程](b04-development.md)，总体进度同步[路线图](development-roadmap.md)。
