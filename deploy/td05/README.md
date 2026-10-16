# TD-05 Windows Docker 候选交付

本说明对应唯一隔离批次 `td05_20261015_01`、项目 `zj-market-td05-20261015-01`、HTTPS `https://zj-market.test:8445`。新 A/B/web 镜像的准确 ID、源码／契约／jar SHA 见 [发布清单](../../docs/team-discovery-td05-release.json)，验收结论见 [TD-05 摘要](../../docs/tests/td05-acceptance.json)。原始私有配置、证书、浏览器截图和运行报告保存在忽略目录 `target/team-discovery/td05_20261015_01`；不得公开该目录。

## 候选操作顺序

1. 核对两仓分支、源码和冻结契约，并从独立 A 源码快照构建；`docs/tests/prepare-td05-release.py` 为本批次一次性构建器。新镜像基于 `deploy/b06/images.lock.json` 固定摘要，不改旧 B-06 镜像。
2. 用封存 B066 备份新建项目、五卷和五张专用网络；`docs/tests/prepare-td05-stack.py --run-name td05_20261015_01` 会校验备份，恢复新卷，以维护账号在克隆 A 库执行两索引迁移，启动新 A 后再启动开关关闭的新 B/web。若恢复过程失败，先核对批次 `prepare-report.json` 和 Docker 归属，不重复执行非幂等 DDL；本批次因默认地址池耗尽已用独立子网接续。
3. 登录并确认发现接口在开关关闭时404。启动时使用 `docs/tests/run-td05-rpc-probe.py` 从候选 B 的实际 Dubbo 库发起签名 TLS A RPC，只在新 B 功能仍关闭时运行；成功报告为 `rpc-readiness-report.json`。A 与 B 运行账号均不可获得 DDL。
4. 仅在真实 RPC 探测成功后将此批次私有 `config/b.properties` 的 `b.team-discovery.enabled` 改为 `true`，只重建隔离 B/web。运行 `node docs/tests/td05-release-gate.mjs target/team-discovery/td05_20261015_01 on`，确认 HTTPS B→A 返回200，再开放候选业务验收。文件更改不自动重启 B。
5. 真实商品／订单验证使用 `docs/tests/td05-real-browser.mjs`、`run-td05-joint.py` 和 `collect-td05-joint.py`；只在新批次中创建商品／活动。最后运行 `collect-td05-release.py` 对镜像、索引、Flyway历史、运行授权、七服务及旧 B-06 历史镜像一致性收口。

## 回退

先把此批次的 B 发现开关关掉并重建隔离 B/web，确认发现路由404、原登录和商品路径可用。若仍需退包，使用 [B-06.7清单](../../docs/b06-final-release.json) 的原 B 镜像；本批次 `verify-td05-rollback.py` 已实测它与新 A 共存，精确镜像 ID 与原清单一致。再升级时恢复 TD-05 B 镜像，等实际发现 RPC 返回200。新增 A 索引是追加结构，回退不删除索引、不还原在线业务数据，也不任意切到未认证旧包。新 B 配旧 A 时发现查询返回503，不能当作可用组合；`verify-td05-old-a.py` 已演示并恢复新 A。

本批次仅在 Windows Docker Desktop、严格 TLS 和模拟支付渠道验收。发布清单是本机候选，不表示镜像仓库推送、Linux验收、其他客户端验收或原 B-06 线上环境升级。原 B-06 七服务、卷、镜像、冷备及历史验收独立保留。
