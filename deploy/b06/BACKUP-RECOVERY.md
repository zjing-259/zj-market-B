# B-06.6 冷备份、独立恢复与兼容发布回退

已完成Windows Docker范围。最终02冷备40项、03已有备份恢复39项、04独立中断恢复11项、16项保护及1项真实ACL回归/12实际权限范围通过。证据docs/tests/b06-backup-acceptance.json、发布docs/b06-backup-release.json、过程16.3。原商城open/READY、无活动告警、逆操作为空；01失败保留。

## 范围与前置条件

Windows Docker Desktop desktop-linux，原项目zj-market-b06和本脚本新建的zj-market-b066-<批次>。完整演练会独占127.0.0.1:443，原商城暂时不可用；不要同时下单、运行watch、启动/停止控制器或另一验收。共享项目、宿主网卡/hosts、默认Docker context不操作。Linux复验仍待实施。

先核对b-06实际Git差异、B065发布指纹、七服务open/READY、所有故障/备份recovery.json为空、Windows>=1.5GiB及完整4.5GiB常驻预算+工具预留、C/D磁盘门槛；脚本会再次检查。原栈停下后才启动恢复栈，不并行驻留两套常驻预算。原五卷永久保留，恢复卷/失败日志也保留；脚本没有删除卷或原库覆盖命令。

```powershell
Set-Location D:/Java/zj-market-b-06
python -B scripts/build-b06-recovery-tools.py --java-home 'C:/Program Files/Java/jdk-21'
python -B docs/tests/test-b06-backup.py
# 仅制作一次封存备份并恢复原商城
python -B scripts/b06-backup.py backup --run-name b066-<fresh-backup>
# 核验完成标记、所有文件hash、镜像配置及归档成员，不启动容器
python -B scripts/b06-backup.py verify --run-name b066-<backup>
# 已封存备份恢复到另一个全新项目/空卷，再验证并返回原商城
python -B scripts/b06-backup.py restore --from-backup b066-<backup> --run-name b066-<fresh-restore>
# 一次完成冷备份、独立恢复、原事件重投、兼容包装发布与失败回退
python -B scripts/b06-backup.py run --run-name b066-<fresh-full>
```

批名必须全新，不覆盖成功/失败目录。所有数据及账号/密钥档案在本工作树私有.local/b06/backups/<batch>，目录使用当前用户/SYSTEM/Administrators NTFS ACL；不得上传到Git或粘贴原档案。这里是本机受控目录，没有加密、异机副本或抗宿主磁盘损毁保证。异机存储/正式秘密保管需在目标环境单独配置。

## 一致性点与备份集合

maintenance仍允许取消及运营恢复，后台任务也继续，因此单设maintenance不构成停写。控制器先写持久恢复意图，切maintenance入口，再停止web、B、A、Broker、NameServer、Redis并核对正常退出；临时restart=no防止意外自动启动。没有worker/consumer/HTTP写入者后导出全部双库业务行及金融指纹，再设置MySQL innodb_fast_shutdown=0、正常关闭并确认exit0；所有自有服务停止后才建立一致性点。

五卷全量保留：mysql-data（A/B业务、模拟渠道、Flyway及系统账户）、redis-data（AOF/RDB）、broker-store（提交日志、消费队列/进度、Topic/组元数据）、broker-logs、namesrv-logs。另备份完整外部密钥/证书/身份签名材料、配置/能力/控制状态/演示账号、原初始化输入/全部原迁移和images.lock、实际使用的普通与维护/SDK及演练工具镜像、确定性全表导出与原始已接收签名事件。

manifest.json逐文件SHA-256，COMPLETE.json最后写入并绑定manifest。缺件、坏hash、输入替换、镜像归档未含声明Config、归档路径逃逸或危险外链均拒绝。SHA校验不是来源签名，档案仅接受本工具生成且由可信所有者保管的版本。失败档案不当作最终成功备份；禁止手改manifest/完成标记绕过。

此做法遵循[Docker卷备份/恢复](https://docs.docker.com/engine/storage/volumes/)和[MySQL InnoDB冷备份](https://dev.mysql.com/doc/refman/8.0/en/innodb-backup.html)的停止写入、完整数据文件与日志保存要求。物理MySQL恢复仅使用相同固定引擎镜像；不作为跨数据库大版本迁移方式。

## 独立空卷恢复与准入

只创建新项目标签的五空卷，拒绝同名已存在卷/容器。归档提取后tar compare验证文件内容、所有者/权限/元数据；卷名、Compose解析后的物理网络名、实际容器网络均必须属于新项目。新资源不会加入原data/mq/rpc网络，服务DNS身份仍为mysql/namesrv/broker/marketing-a/market-b，使用原严格TLS证书与ACL。

不可变bundle与restore-files运行副本分离。先恢复中间件；在worker启动前比对全部A/B业务表及Flyway原行、金融/库存流水/团队名额/原Inbox指纹，再用归档初始化输入验证schema、最小运行授权和迁移账号锁定。入口先保持maintenance，真实身份/商品同步/签名RPC试算通过才开放；恢复栈以新未付订单验证购买、后端checkout开放、原取消/关闭释放。原已APPLIED的PAYMENT_SUCCEEDED签名字节重投两次，等待实际A组消费offset增加，原付款/退款/库存/名额/Inbox指纹不增。

演练恢复项目最终停止，原栈按原镜像/原卷/重启策略受控open恢复，保留恢复卷和原档案。不宣称自动主备提升或覆盖原库。完整表精确比对发生在worker与新验收订单前；后续合法新订单仅在隔离恢复库内。

## 兼容发布与失败回退

B064的数字rosterVersion解析已知不兼容，不作为回退目标。候选发布包装具有不同真实image ID，继承当前已验业务jar；兼容清单绑定V18、schema/history和原jar hash，两镜像实际jar再次核验。验证真实切换、严格HTTPS就绪后开放、健康失败时维持maintenance并实际拒绝新写、回到B065原image ID并复核schema/历史/资金后开放。数据库不降级。此范围只认证同业务二进制的兼容包装回退，不认证未知旧业务版本或真实第三方资金。

## 中断和恢复

```powershell
# 同批逆操作由独立进程读取；不要创建新批代替恢复
python -B scripts/b06-backup.py recover --run-name b066-<interrupted-batch>
python -B scripts/b06-observability.py once
python -B scripts/b06-observability.py status
```

恢复先停止仅该恢复项目，核对原项目容器归属、原镜像及原卷；非重建服务还必须保持原ID。恢复原restart policy，再走原受控open（先关入口、容量/schema/history/权限/真实就绪、后放开）。失败保留recovery.json及FAILED/RECOVERY_REQUIRED，不手工清日志；原归属/镜像/卷漂移时必须诊断，不能自动接管未知实例。备份进程退出不代表商城已恢复，必须核对原七服务、实际HTTPS、资金/库存/名额和共享范围。

## 时间和数据损失边界

记录一致性点、冷备封存、独立全栈就绪、候选开放、失败回退开放、原商城恢复的实际时间。RPO仅保证全部写入者停止后的这一致性点；该点之后原库新交易不在旧备份内。演练耗时包含校验/复制/镜像载入/探测，不是生产SLA；没有在线备份、增量/binlog PITR、自动定时、宿主断电/磁盘损坏或Linux认证。镜像/秘密/协议不兼容时拒绝，不能用清数据或重做新资金事实“修复”。


若恢复原栈时恰在B重建删除/创建之间中断，B缺失会使recover保留意图并拒绝；先确认本批恢复栈已停止、原卷/原发布及state记录匹配，再按B065-D42执行原 `python -B scripts/b06-deployment.py open --context desktop-linux`，之后重试本批recover核对原配置/资金并清理意图。禁止手工清recovery.json或接管未知同名实例。本阶段独立中断专项停在写入者停止之后，未另重复B065已通过的重建缺失窗口演练。




B06-D50（采用推荐，权限核验补修）：最终ACL复核发现旧prepare-b06-secrets.protect_windows依赖Windows PowerShell Get-Acl/Set-Acl模块；本机从PowerShell7继承PSModulePath时安全模块加载失败，旧脚本非终止错误仍exit0，造成目录未关闭继承。改为.NET原生Directory AccessControl、ErrorActionPreference=Stop、显式清理专属私有目录已有ACL再仅授权当前用户/SYSTEM/Administrators FullControl，写后重新读取DACL验证，任何失败拒绝继续。真实Windows临时目录在故意不可用PSModulePath下回归通过；首回归另暴露临时目录已有显式额外主体，严格重建ACL后解决，原失败输出保留，不冒称原帮助函数已有效。

已核实并修复仅本项目.local/b06私有根、runtime/control/observability及01～03备份目录权限，不修改Git/仓库/系统全局ACL、不旋转或改写密钥。04新批由修复后帮助函数创建；最终还需核验根及关键私有文件的实际访问主体。备份内容hash/金额/镜像不变，02/03冷备与恢复证据继续有效；权限保护补修有独立真实回归及最终DACL证明，不说03原执行时已使用最终权限帮助函数。普通应用/协议/旧迁移保持，不因外部ACL工具补修重跑Maven或重建镜像。

真实ACL专项：`python -B docs/tests/test-b06-private-acl.py`。


最终实测时间见验收timings：冷备封存66.257秒，新恢复就绪194.042秒，已有备份停写后恢复就绪204.567秒，兼容候选切换37.364秒，失败回退38.636秒；完整含测试停机560.191/498.418秒，独立中断恢复132.025秒。91个清单文件/3933562408字节本机档案，不是异机容灾；原渠道2340付款/720已退/净1620保持，恢复项目新验收订单未付款。无新普通应用编译/JUnit/完整浏览器套件。下一步B-06.7，Linux尚未验收。
