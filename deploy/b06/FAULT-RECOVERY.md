# B-06.5 单机故障与恢复手册

适用范围：Windows Docker Desktop 的 desktop-linux 引擎、本仓库 b-06 工作树、专属 Compose 项目 zj-market-b06。只用于本机模拟资金验收，执行期间不要从页面另下单。Linux、宿主重启/断电/磁盘损坏、备份恢复和发布回滚没有由此验证；后两项属于 B-06.6。

## 执行前

确认部署 open/READY、七服务健康、严格 HTTPS 可登录，预留现有 4.5GiB 持久服务预算及工具内存；脚本会复核容量、镜像归属、原 schema/Flyway、迁移账号锁定。保留原共享容器和所有数据卷。不会启动/关闭 VMware 或其他项目。普通镜像不含故障工具，工具构建只用已有不可变父镜像和本地依赖。

```powershell
Set-Location D:/Java/zj-market-b-06
python -B scripts/build-b06-fault-tools.py --java-home 'C:/Program Files/Java/jdk-21'
python -B docs/tests/test-b06-faults.py
python -B scripts/b06-faults.py security --run-name b065-<fresh-security-name>
python -B scripts/b06-faults.py run --run-name b065-<fresh-business-name>
```

每次使用全新批次；已有目录拒绝覆盖。脚本持有部署及观测互斥锁，不与 open/stop/watch 并行。新商品/初始库存走运营 HTTP，活动定义及商品映射只新增本批配置；新订单、支付和取消走原 HTTP。退款故障只针对本批自然到期、A 完整核对后确认 ELIGIBLE 的两笔义务，通过独立 verification 进程调用原领域/渠道方法，不 SQL 伪造资金或 MQ 权威事实。

## 中断与恢复

每次动作前先写私有 `.local/b06/faults/<batch>/recovery.json`。容器异常退出先保存原 restart policy，再临时设 no 并 SIGKILL；有序停止中间件也保存逆操作。恢复原策略、启动原容器并验证健康后才移除逆操作。RPC 路径演练先仅在验收 B 容器中临时 extra_hosts 固定 marketing-a 到 A 当前 rpc IP，严格 TLS 试算成功后才断开 B 的 rpc 端点，防止共享 data/mq 网络自动寻址绕过；恢复原 IP/别名并移除临时容器 hosts。不动宿主网卡/hosts、其他网络或全局 Docker 设置。

退款隔离时只临时叠加 `b.refund.scheduler-enabled=false`，核对任务继续工作；恢复时移除叠加文件并重新创建普通 B，验证原 image ID/command。它是受控验收配置，必须恢复后才能继续正常退款业务。成功/失败批都会保留实际商品、订单、渠道事实和原日志，不删除失败事实来通过验收。

```powershell
# 若终端/任务中断，先恢复同一批的残留运行配置，再核对业务。
python -B scripts/b06-faults.py recover --run-name b065-<interrupted-name>
python -B scripts/b06-observability.py once
python -B scripts/b06-observability.py status
```

recover 只处理已保存逆操作；容器 ID 被替换、镜像或归属不匹配会拒绝，不接管新容器。失败逆操作仍保留，其他独立逆操作继续尝试。不要手工清空 recovery.json，也不要重跑失败批为新验收。 若重建在删除旧B/创建新B之间中断，B不存在时recover会保留日志并拒绝；先执行 `python -B scripts/b06-deployment.py open --context desktop-linux`，由原控制器关闭入口并复核容量/schema/权限/原发布及真实就绪，再执行同批recover完成原配置核对。不是recover单命令自动修复；原镜像/归属不符时仍拒绝，不删除日志绕过。恢复容器不代表订单已终局，须使用观测 trace 和原订单/payment/refund/team/event/task ID 查证任务及渠道资金；UNKNOWN 不新建支付/退款键，不以 Broker ACK 替代 A 接受，不在未证明关闭/退款成功时释放库存。

## 预期与证据边界

- A 不可用或 B→A 网络断开：拒绝新支付；关闭意图可持久保留，A 关闭证据未知时不释放库存。
- B 异常退出/创建尝试回执丢失：查询并重放原 operationId 和相同请求，沿用原 paymentId/attemptId。短暂 503 先核对原操作，不直接换键。
- Broker 停止：本地可信付款保留，原 Outbox eventId/body_hash 持久化；恢复后由原消息/A 接受推进成团及唯一库存确认。
- NameServer 停止：新客户端路由探测失败；已有客户端可能使用缓存路由继续，不将其判为故障注入无效。
- MySQL 不可用：公网读取不能返回假成功；观测 queues/obligations 为 null、状态 UNKNOWN。恢复后核对原资金/库存事实。
- Redis 不可用：A 的鉴权 nonce 依赖可能拒绝新支付/关闭查询，保持原订单与库存，恢复后继续。
- 退款渠道已成功但响应丢失：商城保持 UNKNOWN 和同 attempt；另一独立义务继续；普通任务恢复后查询原渠道事实，可在 A 暂不可用时收尾资金/库存，随后同步 A。
- 证书/签名/ACL：正常连接与错误凭据成对验证；越权发布必须在实际既有 topic 上被拒绝，不向业务 topic 发送伪造正向消息。

每项记录真实停止/恢复时间、退出码、健康/任务快照、本地告警以及有限 CPU/内存样本。采样值不是峰值/压力/SLA 保证；SIGKILL 不是断电，当前 OOMKilled=false 不证明历史从无 OOM。健康探针主要是进程/TCP存活，最终另走严格 HTTPS 身份/产品同步/签名试算与数据库资金、渠道、A 名额及唯一流水核对。日志/材料保留在私有 `.local`，公网摘要不得含密码、token、私钥或原敏感请求体。

运行方式依据 Docker 官方的 [重启策略](https://docs.docker.com/engine/containers/start-containers-automatically/)、[即时更新策略](https://docs.docker.com/reference/cli/docker/container/update/) 和 [网络重新连接](https://docs.docker.com/reference/cli/docker/network/connect/) 语义；手动 stop 对重启策略的影响与异常退出不同，因此演练显式保存和恢复策略，不依赖碰巧自动重启。

最终实测为b065-20261012-07：112项实际检查、9项工具测试通过；111项JUnit/33镜像/9维护一致性通过。独立中断恢复b065-20261012-recovery-03、重建缺失b065-20261012-runtime-gap-02均通过，旧01对应旧镜像保留历史。新B/维护/退款工具修复不透明rosterVersion解析，两个实际新团队MQ原字节Inbox接收且无同团队隔离；原隔离不删除/重放。摘要docs/tests/b06-fault-acceptance.json、发布docs/b06-fault-release.json、过程15.3记录实际时间及限制。


2026-10-12用户暂停：修复后07已通过112项矩阵；当前镜像独立中断恢复02被主机内存门槛预检拒绝、未执行故障，runtime-gap-02尚未执行。恢复日志均空，保留正常商城；等待用户明确恢复，再检查资源并用全新批复验。详细过程15.2及docs/tests/b06-fault-progress.json；本阶段不能标最终完成，旧01/06仅为旧镜像证据。


专项中断恢复复验（独占演示环境、新批次；第二项会停止/移除仅本项目临时B容器，不删卷）：

```powershell
python -B docs/tests/run-b06-interrupted-recovery.py --run-name b065-<fresh-recovery>
python -B docs/tests/run-b06-runtime-gap.py --run-name b065-<fresh-runtime-gap>
```


2026-10-12最新收口：B06.5当前候选07的112项矩阵及NameServer recovery-03、B缺失runtime-gap-02均通过，全部逆操作已收口；原暂停/旧候选/失败批为历史，不覆盖。B缺失仍需手册的受控open再recover两步。七服务open/READY，无活动告警；最新发布/验收见docs/b06-fault-release.json、docs/tests/b06-fault-acceptance.json。

B06-D44（采用推荐，最终观测补修）：修复通知解析后，一条TEAM_FAILED原消息晚于同团队RESOLVED及本订单全额退款/A同步/库存释放到达，原接收器合法保留DEFERRED_B05交接行，发现器不会重建已有核对任务。它不是仍待退款的义务；旧只读观测把next_attempt_ms=0视作从纪元起积压，最终汇总因真实活动告警拒绝。保持原行、原调度和原证据，不SQL清DONE、不清告警、不扩大自动重放。仅把严格绑定且已全部收尾的TEAM_FAILED/TEAM_RECONCILIATION_REQUIRED交接行单列historicalSettledHandoffs：必须DEFERRED_B05、无租约、原evidence hash一致、原source/channel/team与订单和RESOLVED任务一致，订单CLOSED、付款SUCCEEDED/ACCEPTED、同payment全额退款SUCCEEDED/ACCEPTED/RELEASED、预占RELEASED、恰一RELEASE且无CONFIRM/履约/非核对ACTIVE阻断或REVIEW工作。任一缺证或矛盾仍计活动，REFUND_OBLIGATION不走此分类，原审核/隔离/资金投影保持。实现只涉及外部SELECT-only/TLS观测脚本，不修改镜像、权限、迁移或资金规则。

D44验证：新增3项隔离关系测试执行同一SQL谓词，覆盖两类有效交接及30个缺证/错误绑定/活跃租约/未同步/金额不全/重复释放/确认或履约/审核等反例；7项原观测与9项故障工具回归通过。真实MySQL原观测账号查询通过，BLOB证据按UTF-8显式转换后读取JSON；第一次缺少转换的SQL验证返回UNKNOWN并保留诊断，不冒称成功。最终历史交接1、活动trade-work 0、所有资金义务/库存预占/活动审核0，原backlog:b_trade_work同incident恢复，无活动告警。未删除原交接、隔离或审核记录。该补修在07业务矩阵与两项恢复之后完成，只读真实终态再次汇总通过，不伪称07每一历史采样使用了新口径；最新observer/测试hash及补充验证见tests/b06-fault-acceptance.json的observerHistoryClassification，原业务源码/普通镜像未变，无需重跑资金矩阵或镜像构建。
