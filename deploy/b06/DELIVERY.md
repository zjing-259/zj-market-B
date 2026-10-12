# B-06 最终交付：Windows＋Docker

本手册以最终验收 `docs/tests/b06-final-acceptance.json`、候选清单 `docs/b06-final-release.json` 和交付索引 `docs/b06-delivery-manifest.json` 为准。只认证本机 Windows Docker Desktop 的 Linux/amd64 容器；Linux虚拟机、其他局域网客户端与公网未验证。支付和退款是独立持久模拟渠道，没有真实第三方扣款。

## 交付内容与入口

公开源文件ZIP位于 `.local/b06/delivery/<批次>/zj-market-b06-public.zip`；旁边 `manifest.json` 和 `COMPLETE.json` 绑定逐文件SHA256与ZIP指纹。包内 `DELIVERY-MANIFEST.json` 记录精确文件集合、基线HEAD和工作树未提交事实。执行 `python -B scripts/b06-delivery.py verify --directory <交付批次绝对路径>` 校验ZIP内容和完成标记；文件修改后必须重建新批次，不覆盖原交付。

公开包不含镜像层、实际数据、私钥、密码、浏览器会话或A冻结二进制。它是源码/配置模板/证据/操作说明，不能脱离私有输入直接离线启动。已有一致冷备 `.local/b06/backups/b066-20261012-02` 含五卷、配置/密钥、初始化输入和不可变镜像，约3.93GB；它是本机NTFS限制权限的未加密私有材料，不能和公开ZIP一起公开分享。原始A二进制独立按 `b06-a-release-manifest.json` 保管，不宣称脏A工作树可复现它的源码构建。备份不包含原A构建输入三件套，不能替代原A二进制供应；备份已含可直接运行的A镜像。

部署源码入口 `README.md`；受控启动 `scripts/b06-deployment.py`；观测 `OBSERVABILITY.md`；故障 `FAULT-RECOVERY.md`；备份与回退 `BACKUP-RECOVERY.md`。正常应用不含verification/Flyway，不用运行账号执行DDL。

## 现有本机运行、停止与维护

在本工作树根目录使用Python3、既有依赖和Docker Linux引擎。以下不会初始化或清空数据库：

```powershell
python -B scripts/b06-deployment.py status --context desktop-linux
python -B scripts/b06-deployment.py ready --context desktop-linux
python -B scripts/b06-observability.py once
python -B scripts/b06-observability.py status
./scripts/open-b06-browser.ps1
```

最后一条只在专属Edge配置中把 `zj-market.test` 解析到127.0.0.1，使用当前用户受信CA与严格HTTPS；不改hosts。账号密码从本机私有 `.local/b06/control/demo-accounts.json` 查看，不粘贴到报告或Git。入口只有443；MySQL/Redis/RPC/MQ无宿主公开端口。Cookie保持Secure/HttpOnly，不通过忽略证书错误访问。

```powershell
# 关闭新交易，保留既有恢复能力；不等于停所有写入者
python -B scripts/b06-deployment.py maintenance --context desktop-linux
# 仅本项目停机，保留卷
python -B scripts/b06-deployment.py stop --context desktop-linux
# 维护启动并校验；完成就绪核验后开启新入口
python -B scripts/b06-deployment.py start --context desktop-linux
python -B scripts/b06-deployment.py open --context desktop-linux
```

受控open先关闭入口再核对资源、schema、迁移、权限和真实依赖，失败保留维护入口。禁止用原始 `compose up` 绕过能力门槛；禁止 `down -v`。本地观测watch需显式开启：`python -B scripts/b06-observability.py watch`，每次重启后重新运行；无常驻watch时不承诺持续告警，过期指标为UNKNOWN。查看private观测文件或trace定位具体订单/支付/退款/团队/事件/任务，MQ consumer lag未采集。

## 新环境首次初始化

这是安装流程，禁止在已有部署上生成新秘密或重做初始化。先准备Python依赖 `python -m pip install -r scripts/requirements-b06.txt`、JDK21、Maven、Node/npm、Docker Linux引擎和足够资源；完整栈由容量门槛动态判断，Windows可用内存至少1.5GiB只是其中一项。

1. 保管并按清单校验A冻结三件套，用 `./scripts/stage-a-release.ps1 -ArtifactDirectory <三文件目录>` 导入；不从脏A工作区替换来源。
2. 依README构建B和前端，再生成全新私有秘密：`python -B scripts/prepare-b06-secrets.py --java-home 'C:/Program Files/Java/jdk-21'`。已有目录时拒绝覆盖是保护，不能删除绕过。随后构建普通镜像、SDK与维护镜像：`build-b06-images.py`、`build-b06-tools.py`、`build-b06-maintenance.py`，均按 `--java-home` 参数及README执行。
3. 检查新生成release.env与本次镜像ID。重建结果是新的候选，需重新验收，不能冒充最终候选内容ID不变。如交付既有候选则用备份中的 `images.tar` 加载精确ID，按BACKUP-RECOVERY恢复配套配置/数据。
4. `python -B scripts/b06-deployment.py init --context desktop-linux` 只接受归属明确的专属环境，完成A空schema/B19条迁移（最高V18）、48表B最小权限、运行/迁移分离、迁移账号锁定、MQ/演示种子。再start、ready、open；浏览器信任使用专属CA与脚本。
5. 演示样本的活动有时效；过期不是部署失败，使用新的验收批次准备商品/库存/活动，不修改旧订单、原键或历史事实以重新展示。首次空业务库初始化证据属于B062；最终本轮使用五个空卷从封存备份恢复，不混称两者。

## 浏览器演示与验收复现

专属Edge访问商城，买家一选择商品开团并模拟成功支付，买家二在该团队参团并支付，查看成团成功/库存确认/待履约；可先模拟失败再重试，仍保持同一支付根。另一独立商品只付一名成员，等待自然过期及完整核对、全额模拟退款、A同步和库存释放。第三笔未付订单申请关闭，确认最终释放。运营查看库存、核对与退款页；刷新页面不能写业务，普通买家不能访问运营或别人的订单。

最终复现入口（停原栈，独占443，新卷/网络，结束自动恢复原栈）：

```powershell
python -B docs/tests/run-b06-final.py --run-name b066-final-<fresh> --from-backup b066-20261012-02
```

该命令需现有封存备份和当前配套固定工具/源指纹；不是无私有输入的公开演示命令。真实Edge必须已信任备份同源web CA；新机器重新验证信任，不能设置ignoreHTTPSErrors。断开时按同批次 `python -B scripts/b06-backup.py recover --run-name <原批次>`，不要新建批次替代恢复。演练只写恢复项目新样本，原商城资金/渠道/库存/名额保持。成功/失败原始日志和停止后的恢复卷保留。

## 证据和发布限制

最终候选清单逐阶段关联报告及hash；旧失败/暂停/补修是历史，不修改成成功。B063旧镜像浏览器报告仍是旧证据，本轮B067重新认证当前B065候选。B065含真实rosterVersion原字符串修复与111项JUnit、故障112检查；B066含冷备/恢复/同业务jar包装回退，不宣称任意旧业务二进制回退。最终交付不重复全部有破坏性的故障；引用其精确固定镜像证据，再实际新环境恢复、重复消息、包装回退及完整浏览器闭环。

当前只能兼容包装回退，不认识V14～V18/原opaque ID的旧版本禁止使用；无数据库自动降级。RPO仅完全停写的一致性点，后续原交易不在旧备份；时长为有限样本，非SLA。无在线/PITR、异机、宿主断电/损盘、真实第三方资金、发货/收货、主动退团/部分退款、通用REVIEW解除或HA认证。历史已结清审核/隔离和待依赖项保留；业务规则不因交付放宽。所有交付为本机成果，尚未Git提交/合并/推送或上传镜像仓库。

## Linux接续清单（待验证）

保留旧CentOS7虚拟机，推荐另备Ubuntu24.04 LTS amd64；4vCPU/8GiB/80GiB为建议，资源、维护版本、Docker/Compose、时钟/NTP、可用空间均需实测。桥接或明确NAT映射下核实宿主和其他LAN客户端可达、稳定IP/域名、443防火墙与SSH权限；当前127.0.0.1验证不代表局域网部署通过。

同一候选通过docker save/load迁移并校验内容ID；新主机用独立项目/卷/秘密，按UID/GID核验文件权限和只读挂载。Windows绝对路径、desktop-linux context、Edge路径、NTFS ACL与Windows资源探测不能直接复制为Linux认证：当前Python控制器仍有固定本机路径/context，需显式移植与复验，不能声称现脚本直接支持Linux。重新核对所有SAN/链信任、RPC mTLS、MQ TLS/ACL、DB VERIFY_IDENTITY；Redis仍内网密码认证明文。依次重跑空库初始化/最小权限、严格浏览器闭环、观测/故障/备份恢复/兼容回退，并生成独立Linux证据，方可标Linux完成。不要复制运行中的Windows卷目录。
