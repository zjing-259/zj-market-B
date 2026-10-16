# TD-06 主商城与候选入口

TD-06.1建立了日常商城和隔离候选的显式入口；TD-06.2已把日常 `https://zj-market.test`（443）升级为新 A/B/web。候选 `https://zj-market.test:8445` 仍运行 TD-05 镜像。两者使用不同数据库／Redis／MQ卷，不能互换；443原五卷未被替换。

## 选择正确入口

从 `D:/Java/zj-market` 执行，必须显式选择目标。脚本只信任当前用户的项目 web CA，使用专用 Edge 配置把 `zj-market.test` 指向 `127.0.0.1`，保持证书域名校验，不修改全局 hosts、不忽略证书错误。两个目标使用不同浏览器配置目录，避免同域名跨端口会话混用。首次导入 CA 可先用 `-ConfigureOnly`；已有 B-06 CA 时只复用，不夺取原信任记录。

```powershell
pwsh -NoProfile -File scripts/open-team-discovery-browser.ps1 -Target main443 -StatusOnly
pwsh -NoProfile -File scripts/open-team-discovery-browser.ps1 -Target candidate8445 -StatusOnly
pwsh -NoProfile -File scripts/open-team-discovery-browser.ps1 -Target candidate8445 -ConfigureOnly
pwsh -NoProfile -File scripts/open-team-discovery-browser.ps1 -Target candidate8445
```

`-StatusOnly` 不打开浏览器、无需导入 CA；它验证目标项目、镜像与服务就绪。日常 443 入口可用 `-Target main443` 打开，默认不会被改到8445。若需移除本脚本首次导入的项目CA，用相同目标加 `-RemoveTrust`；原本已存在的信任不会被它删除。所有口令继续留在忽略的私有目录，公开说明不包含密码。

## 候选启停与就绪

`scripts/td06-environment.py` 必须带 `--target`。`candidate8445` 只操作 TD-05 项目，检查 Compose 项目名、七服务／镜像、专用五卷／网络／私有只读挂载、回环8445、配置SHA、schema／Flyway和A查询索引；其实际停启与严格TLS查询已通过。升级后 `main443` 委托 [TD-06.2主发布控制器](../../scripts/td06-main-release.py)：核验原项目卷、目标镜像、追加索引、B Flyway及HTTPS发现门禁；受控启动先关闭入口，再恢复中间件／A／发现关闭B与网页、探测实际签名TLS RPC，最后启用发现并开放入口。原 B-06 控制器固定旧schema指纹，不能用于升级后443的启停。

```powershell
python -B scripts/td06-environment.py status --target candidate8445
python -B scripts/td06-environment.py ready --target candidate8445
python -B scripts/td06-environment.py stop --target candidate8445
python -B scripts/td06-environment.py start --target candidate8445
```

443日常检查／停启命令如下。`stop` 保留原五卷和业务键；`start` 重新执行门禁，绝不从旧备份覆盖在线数据。发布私有控制状态位于忽略的 `target/team-discovery/td06_2_main_20261015_01`，不得删除或提交其中凭据路径材料。

```powershell
python -B scripts/td06-environment.py ready --target main443
python -B scripts/td06-environment.py stop --target main443
python -B scripts/td06-environment.py start --target main443
```

TD-06.2私有一致性备份批次为 `D:/Java/zj-market-b-06/.local/b06/backups/b066-td062-20261015-03`，一致性点2026-10-15T14:32:02.619Z；上线后再次运行既有备份工具的全文件哈希核验通过。本批未另做空卷恢复，恢复工具的隔离演练证据属于先前B-06.6批次；其旧数据卷镜像用于灾后隔离恢复，不用于升级后有新交易的在线回退。追加索引不回滚。兼容回退已在443原卷实测旧B/web包，验证原试算及未付订单创建、取消和关闭，再切回新包；执行过程和镜像ID见 [验收摘要](../../docs/tests/td06-2-acceptance.json)。任何新的回退先维护入口、核对当前资金与待处理义务，只切兼容包，不还原旧备份至原卷。

## 可更新的演示团队

候选演示批次 `td06_demo_20261015_03` 已由隔离候选的运营账号创建商品 `TD06 演示 td06_demo_20261015_03`，增加10件库存、60分钟两人团活动；甲（私有账号 `b06buyer`）已通过正常页面开团并模拟付款，且付款被A接受。乙（`b06buyer2`）已在商品详情看到同一团队并验证原团队详情可JOIN。商品详情地址：`https://zj-market.test:8445/products/d3addf1e-d5d7-462a-8403-074bcc424c08`。该团队在 **2026-10-15 23:11:20 Asia/Shanghai** 到期；到期、满位、甲自己查看、未登录或乙已有同SKU订单时列表为空或显示原订单属于正常业务。

该2026-10-15样本已过期，仅留历史演示证据。需要重新演示时，先生成新批次并运行 `python -B docs/tests/verify-td06-demo.py` 检查新批仍可加入，再用候选专用Edge登录乙，从商品详情点击“去参团”，在既有团队页核对参团报价、确认JOIN并通过原模拟支付流程完成。私有账号密码在候选 `target/team-discovery/td05_20261015_01/private/control/demo-accounts.json`，不要复制到公开文档。目标443实际付款成团已在TD-06.3验收。

样本过期后，用**新批名**重新执行 `node docs/tests/prepare-td06-demo.mjs td06_demo_YYYYMMDD_NN`。脚本仅在8445创建全新商品、库存、有效活动和甲的真实模拟付款，再用乙浏览器确认可见；从输出读取新商品地址与截止时间。不要修改旧团截止、已收款时间、人数或库存流水来延长展示。若付款操作响应未知，保留同批报告并用 `--resume` 沿原订单恢复；不要重复下单。原始报告和失败证据在忽略的 `target/team-discovery/`，不提交私有会话、凭据或截图。

商品页列表源码已统一为首屏3条、携原游标的“查看更多”每次10条，前端构建与Edge模拟HTTP6项通过。**443现运行TD-06.2新web镜像；8445仍是TD-05已验旧web镜像，续页仍为3。** 443真实发现JOIN、成团、自然失败退款和逐单守恒已由TD-06.3批次通过；当时不足四个同时可加入团，未人为造长期付费团强测真实多页，分页参数沿用TD-06.1测试。列表要求登录、至少一位成员付款且A已接受、团未过期有空位；502／503表示查询失败，不能当作空列表。

## 主站443交易验收（TD-06.3，2026-10-16）

脱敏结果见[TD-06.3验收摘要](../../docs/tests/td06-3-acceptance.json)，私有原始报告位于忽略目录 `target/team-discovery/td06_3_main_20261016_01`。25项真实Edge检查、11项逐单A/B／渠道／库存核对和14项终态列表只读检查通过。模拟渠道累计实收2610.00元、累计退款810.00元；主商城库存可用570、预留0、已售20，其中本批三个新品各入库10件并售出2件。原待办哈希键零丢失，新增义务继续自然处理。无需重复对原批下单；下一批须使用新的批名和操作前快照。当前源码和镜像未推送。

## TD-06.4 本机归档与复核

[发布清单](../../docs/team-discovery-td06-release.json)和[两仓源码锁](../../docs/team-discovery-td06-source-lock.json)绑定当前主站A/B/web镜像、契约及构建JAR、前端构建、公开配置模板、A schema／索引、B Flyway和忽略目录下的原始证据哈希；私有账号、证书、会话与备份内容不进入公开清单。需要只读复核时执行：

```powershell
cd D:\Java\zj-market
python -B docs/tests/collect-td06-4-release.py check
```

日常用户从 `https://zj-market.test` 登录后打开商品详情；团队至少一人付款且A已接受、仍未过期、有空位，且当前用户无同商品进行中订单时才可推荐。`B_TEAM_DISCOVERY_ENABLED` 的当前主站受控配置为开启；回退或缺新RPC时按TD-06.2门禁先关闭发现，旧商品／开团／订单／支付恢复路径保持可用，不把503当作空列表。候选8445具有独立浏览器配置和数据卷，历史团队已过期。

归档范围是本机Windows Docker Desktop及模拟渠道；Git提交／推送、镜像仓库上传、Linux及外部客户端验证均未执行。TD-06.2升级前冷备只对应当时一致性点，不能覆盖已产生新交易的主卷。重复验收需建立新批次，保存新的前后快照与报告，不改写TD-04／05或本批证据。
