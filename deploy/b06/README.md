> B-06.0～.7已完成Windows＋Docker范围，最新候选、验收、公开交付与Linux接续见[最终交付手册](DELIVERY.md)。下方各阶段状态保留历史，不代表当前接续。

> 当前B-06.2已完成Windows Docker范围，35项联合/33项普通镜像/9项维护工具检查通过。七服务已受控open/READY；阶段原始证据与限制见docs/tests/b06-startup-acceptance.json，当前发布指纹见docs/b06-startup-release.json。B06.3浏览器闭环及Linux目标未验。

# B-06 Windows Docker 镜像、网络与配置

以下镜像章节记录B-06.1；B-06.2操作入口见文末。Windows Docker Desktop使用Linux/amd64引擎；Linux服务器暂由此环境替代。完整空库初始化/权限/种子数据/业务能力开启属于B-06.2，当前不能直接把`compose up`当作完整商城已可用。路线图25.11及B-06过程11记录方案与验收。

## 构建输入与命令

B与前端从本工作树构建；A仅使用b06-a-release-manifest.json批准的本机冻结二进制，不从A脏工作树重建。A派生包移除所有内嵌application环境配置及旧logback配置，编译a-overlay两项源码：Redis密码必填配置和无业务写入的存活探针。原始A保持不变，原包/派生包/适配源码/镜像分别记录hash；不声称可重复构建原始A源码。

在项目根目录执行（Python3依赖锁见scripts/requirements-b06.txt（cryptography/PyYAML）；JDK21仅用于B构建和编译Java8适配；Maven入口保持A全局JDK不变）：

```powershell
./scripts/mvn.ps1 -JavaHome 'C:/Program Files/Java/jdk-21' -B package
Push-Location frontend
npm ci
npm run build
Pop-Location
python -B scripts/prepare-b06-secrets.py --java-home 'C:/Program Files/Java/jdk-21'
python -B scripts/build-b06-images.py --java-home 'C:/Program Files/Java/jdk-21'
python -B scripts/build-b06-tools.py --java-home 'C:/Program Files/Java/jdk-21'
docker --context desktop-linux compose --env-file .local/b06/build/release.env -f deploy/b06/compose.yml config --quiet
python -B docs/tests/run-b06-security.py --run-name b061-<fresh-name>
```

若已存在runtime材料，跳过prepare-b06-secrets，禁止删除/重建以绕过错误；轮换需独立受控操作。脚本不安装操作系统信任、不改hosts/防火墙，不输出秘密值。生成器默认拒绝覆盖；构建目录仅允许列出的文件，普通镜像不含工具/verification/Flyway/源密钥/.local目录。生成或验证失败保留原证据，重新验收使用新名称。tools镜像显式调用，Compose正常启动不包含工具。

`images.lock.json`固定实际基础镜像digest；RocketMQ沿用本机已验证的镜像镜像站副本摘要，不隐式更换来源。应用镜像的`release.env`使用本地内容ID，`release-manifest.json`记录标签/ID/输入hash，不伪称已上传的registry manifest digest。另一台机器可通过`docker save`/`docker load`迁移同一组本地镜像；重新构建会重新记录ID。Linux路径由B06_SECRET_DIR提供，不复制Windows绝对路径作为服务器配置。

## 网络与安全配置

web唯一发布443，Windows默认127.0.0.1，只接受HTTPS；目标域名zj-market.test，SAN匹配。以后局域网演示需明确B06_BIND_IP、域名解析与客户端信任；不得用`-k`或关闭Secure cookie代替验收。此阶段容器内客户端用显式CA和解析映射验证，尚未安装Windows根证书/hosts，真实浏览器身份流程属于.3。

五张网络：edge(web/B)、rpc(A/B)、data(A/B/MySQL)、redis(A/Redis)、mq(A/B/NameServer/Broker)。后四张为internal；数据库/Redis/RPC/MQ不发布端口，不借用开发网络/卷。Broker公布broker:10911，VIP10909由SDK实际验证。Nginx通过Docker DNS重新解析B，保留/api完整路径、Origin/Host及HTTPS转发头；Nginx覆盖客户端自带转发头，B使用native转发处理且不对宿主开放HTTP；API错误不回落SPA，拒绝公开/internal。

普通A/B/web非root且只读根文件系统；临时目录有上限、掉所有capabilities。MySQL原入口负责所需初始化权限；MQ仅一次性mq-permissions容器使用root初始化专属卷的3000 UID，常驻进程仍为镜像自带rocketmq用户。MySQL复制公开配置至Linux临时目录chmod644后加载，避免Windows文件挂载权限导致忽略配置；秘密不依赖MySQL读取world-writable客户端配置。

RPC用独立服务端CA/客户端CA与双向TLS，叠加原请求HMAC。MQ4.9.7实际属性为`-Dtls.server.mode=enforcing`，NameServer和Broker都强制TLS、test mode=false；客户端authServer=true。SDK未提供这里需要的DNS身份校验，因此只信任实际MQ服务叶证书；NameServer/Broker共用该证书，证书SAN覆盖二者。未知CA和同CA不同叶证书均必须拒绝；证书轮换需同步可信材料。MQ应用账号默认DENY，四业务Topic和五消费组精确授权；admin只在隔离工具中使用。Broker内部管理NameServer有TLS，但4.x NameServer无此Broker ACL，不把网络隔离当独立Nameserver授权。

MySQL强制secure transport，A/B运行账号REQUIRE SSL，JDBC VERIFY_IDENTITY及独立PKCS12信任库；.2将完成精确表级权限和空库迁移。Redis需要密码，A适配保持JsonJacksonCodec/池/超时语义；受原A客户端协议限制目前为专属内网认证明文，不宣称Redis TLS。

每服务只挂载必要的公开证书、私钥及秘密属性。CA私钥留runtime/private，普通容器和验证容器都不可见；验证工具只挂载白名单的测试材料。Compose file secrets属于本机只读文件挂载，不提供Swarm秘密加密保证，宿主材料目录由本机账户保护。[Docker secrets规范](https://docs.docker.com/reference/compose-file/secrets/)和[服务配置规范](https://docs.docker.com/reference/compose-file/services/)作为配置参考；RocketMQ行为以固定4.9.7字节码及真实负向证据为准，通用TLS文档的旧属性不能代替实测。

## 启动边界与验证

A/B存活探针只证明HTTP进程可响应，不检查资金/数据库就绪，不执行任务。完整栈启动必须等.2迁移/48表权限/schema检查；B公开模板初始关闭新业务能力，身份/数据库装配仍要求真实schema，不用自动迁移掩盖缺失。各recovery默认语义保持，禁止把新入口关闭等同旧义务清空。

安全验收使用独立项目、空A安全数据库和参数校验RPC，不种植订单/付款/退款；B fixture显式关闭数据库/身份/RPC/MQ，只验镜像进程和HTTPS/API路由，不能冒称完整B依赖启动。测试完成只移除自有项目容器/网络，独立卷保留诊断，不清理共享数据。资源峰值和完整商城容量仍须.2准入复核。


## 本轮已验证结果与接续

最终B06.1：107项JUnit/前端42模块、33项镜像内容与隔离检查、b061-security08的30项真实容器检查、Windows宿主严格HTTPS补验和最终同指纹重复构建通过。公开摘要见docs/tests/b06-images-acceptance.json、镜像清单docs/b06-image-release.json；私有原始报告/失败样本留.local/b06，不进入Git。

B外部配置用spring.config.additional-location，保留包内自动装配排除及默认安全值，再加载公开配置和秘密覆盖；A派生包已删所有环境配置，因此仅A使用spring.config.location替换加载。B健康控制器通过现有显式Import装配并增加正常启动路由回归。

Windows材料生成器收紧新输出目录ACL为当前账户/SYSTEM/Administrators；本轮.local/b06已同样收紧，现有材料禁止覆盖/隐式轮换。Linux未来接续仍需按各服务UID/组校验宿主秘密文件权限，不把Windows挂载权限当Linux已验证。

Windows Schannel curl在本地CA无吊销分发信息时返回revocation unknown；本轮没有使用-k或关闭吊销检查，而用Node宿主客户端显式CA、DNS主机名和rejectUnauthorized=true补验。容器curl也严格校验证书链/主机名，错误CA和SAN均拒绝。OS根信任/hosts及真实浏览器登录仍未安装/运行，归.3。

安全验证容器和网络已清理，专属失败/成功测试卷保留诊断，原17个容器保持。本轮不常驻展示商城，不启动Linux VM、不改其网络，不发布Git或镜像。下一阶段.2先复核实际容量，再实现专属完整A schema和B V18显式迁移/48表权限、Topic/组初始化及受控业务启动。


### B-06.2 操作入口（Windows Docker）

数据库与演示数据由独立维护工具显式初始化，普通A/B启动不执行迁移。使用本工作树根目录、Python3/JDK21和已安装Node；所有Docker命令显式desktop-linux。第一次须先按上文准备外部材料、A/B/web及SDK工具镜像，再执行：

```powershell
python -B scripts/build-b06-maintenance.py --java-home 'C:/Program Files/Java/jdk-21'
python -B scripts/b06-deployment.py init
python -B scripts/b06-deployment.py start
python -B scripts/b06-deployment.py open
python -B scripts/b06-deployment.py status
```

init只操作zj-market-b06自有项目、新命名卷及group_buy_market_b06/zj_market_b06。遇已有无归属记录的项目/卷拒绝接管；已有材料不重建。A的净DDL来自当前已含phase1及通知租约列的基础SQL，提取器保留引号内分号；仅保留必要reaudit/通知状态元数据变更及v2建表，waiting主键已为consumer/producer/event_id，不重复ALTER。来源及派生hash见init/a-schema-provenance.json；A二进制原构建源码提交仍未知。

B通过原V1～V18（含V10_1，19条版本迁移）显式Flyway迁移/校验。a_runtime仅22表、b_runtime仅48表DML，REQUIRE SSL；不能DDL、读迁移历史/初始化记录、跨A/B库或授予权限。a_migrator/b_migrator只在显式迁移时解锁，finally锁回；普通服务不挂载迁移密码。A每条DDL先记PREPARED，再执行并记APPLIED；中断/输入冲突拒绝自动重放，须查清真实DDL后另记恢复审计，不以删除卷/修改旧迁移修复。

start表示维护模式：所有恢复能力运行，checkout及新核对/退款发现关闭；网关默认拒绝API写入，放行身份、只读POST试算、取消和既有运营恢复控制。open先关网关新写入、检查schema/迁移历史/权限/资源、重建B加载能力文件、验证真实商品同步/严格HTTPS登录/签名A试算，再开放。切换时显式重建B，不能依赖挂载文件改变触发Compose重建。模式切换期间存在短暂不可用；A/B存活不等于业务就绪。失败保持网关关闭，FAILED_GATE_CLOSED不冒称能力重配完成；网关重建失败时停止本项目web，修复后重新执行start/open。

```powershell
python -B scripts/b06-deployment.py maintenance
python -B scripts/b06-deployment.py ready
python -B scripts/b06-deployment.py stop
python -B scripts/b06-deployment.py start
```

stop正常停止本项目服务并保留卷；下次start从原卷维护启动，再显式open。Docker重启时常驻容器按原配置恢复；如果此前open且没有执行stop/maintenance，不能声称重启自动变为维护。实际操作模式及阶段记录在.local/b06/control/state.json，受命令文件锁保护；status同时显示网关模式、阶段与容器状态。

演示账号b06operator、b06buyer、b06buyer2的随机密码只保存在.local/b06/control/demo-accounts.json；不在终端/文档输出。B商品、库存和Outbox走既有领域服务，种子事务及稳定入库operationId保证重放不加库存；A只种活动600001、数值折扣ID60000101及b06/web映射。原二进制Mapper要求数值折扣ID，不从当前A源码类型推断兼容。重复初始化不重置账号、商品、库存、活动截止时间或旧业务事实。

普通服务上限合计4.5GiB，冷启动要求Docker可用（加本项目已运行占用）≥4.75GiB、Windows可用≥1.5GiB、C≥20GiB/D≥80GiB。192MiB只读运行校验占用该额外预算；512MiB迁移/种子只在受控初始化或显式验收重放时使用，调用前另检查实际可用内存。所有数值只用于当前本机演示准入，最终Linux和生产容量另验。

专门联合验收只适用于尚无支付/退款的B062演示环境，运行时不要并行操作该演示商城。脚本会创建并关闭一笔新的未支付订单、短暂停止本项目A、验证维护模式恢复和库存只释放一次，临时增/删专用schema检查字段/约束、重放迁移和种子、创建全新私有测试环境，再冷启动原卷并受控开放；共享服务和A工作区不改动。失败批次不覆盖；专属测试容器/网络清理、卷和私有证据保留：

```powershell
python -B docs/tests/run-b06-startup.py --run-name b062-<fresh-name>
```

入口域名仍为https://zj-market.test，宿主只发布127.0.0.1:443。此阶段用Windows Node显式CA和原DNS身份严格验证，不安装系统根信任/hosts；真实浏览器证书/域名配置及购买付款成团/失败退款闭环留B-06.3。Linux VM、观测/故障演练、备份/恢复和交付仍留后续阶段。


本轮收口复核：

```powershell
python -B docs/tests/verify-b06-maintenance.py --run-name b062-tools-<fresh-name>
python -B docs/tests/collect-b06-startup.py --run-name b062-startup03
```

collect只汇总已通过的当前批次与本地只读状态，不重跑验收或替代新阶段证据。实际固定A/B镜像与B06.1一致，web更新维护门禁，维护/SDK工具各自固定本地内容ID。A净DDL以.gitattributes保留精确字节，原B迁移不改；Linux交付/重建还需按发布归档校验全部字节与权限。

### B-06.3 浏览器入口与正常闭环（已完成Windows Docker范围）

Windows hosts由VPN管理，使用专用Edge配置的域名解析规则，不改全局hosts或代理。专用浏览器只访问本机商城；HTTPS仍严格校验。首次在本机交互式PowerShell执行，Windows若显示安装证书警告，请核对为本项目web CA（指纹记录.local/b06/control/browser-trust.json）后确认：

```powershell
Set-Location D:/Java/zj-market-b-06
./scripts/open-b06-browser.ps1 -ConfigureOnly
./scripts/open-b06-browser.ps1
```

只信任当前用户商城web CA，其他RPC/MQ/MySQL CA不导入；私钥不安装、不拷出。普通浏览器直接输入域名仍需自己的DNS解析，因此应从该入口打开专用浏览器；不影响其他浏览器配置。不再使用时可执行./scripts/open-b06-browser.ps1 -RemoveTrust，仅按本轮归属记录移除精确证书，保留浏览器数据。撤销后该商城HTTPS会再次拒绝，恢复需重新导入。

证书未信任时，严格浏览器返回ERR_CERT_AUTHORITY_INVALID，不能点击忽略或以此声称验收通过。最终b063-20261012-02已通过24项浏览器与11组守恒检查，摘要docs/tests/b06-normal-acceptance.json。新验收需独占操作本机演示商城，使用新批次，不重置已有数据：

```powershell
npm install --prefix target/b06-browser-runtime playwright@1.64.0 --registry=https://registry.npmjs.org --no-audit --no-fund
python -B docs/tests/run-b06-normal.py --run-name b063-<fresh-name>
python -B docs/tests/collect-b06-normal.py --run-name b063-<same-name>
```

脚本使用真实Edge、A/B/MySQL/MQ和独立模拟渠道，首先检验可信HTTPS；下单与付款从页面操作。新B商品/10初始库存走原运营API，A仅新增活动和映射；成功活动15分钟、自然失败活动2分钟，绝不改已成立团队/paidAt。失败批次原样保留，不自动删除已创建商品或业务事实。截图/本批报告在.local/b06/browser，敏感账户仅使用既有私有文件，浏览器token只存在内存。collector须浏览器和守恒全部实测通过才生成b06-normal-acceptance.json；当前最终摘要为b06-normal-acceptance.json，b06-normal-progress.json为接续状态；不可把旧批次当新验收。

最终B063状态：七服务健康open/READY，应用镜像与B062相同。独立测试商品/订单/团队与旧失败/中断批保留。失败订单全退关闭后现有TEAM_FAILED审核标记和所属核对block仍保留，不提供清标记按钮；退款/A同步/库存实际三状态均完成，运营定位须结合任务终态。订单页A团队状态属于既有证据快照，当前团队以团队详情查询为准。下一阶段B06.4处理观测，Linux未验。


### B-06.4 轻量观测（Windows Docker已验收）

入口、指标/告警口径、六种关联查询及恢复步骤见[观测运行手册](OBSERVABILITY.md)。专用SELECT-only账号，once/watch/status/trace无公网诊断接口；watch须显式运行，重启后不自动启动。最终39项真实检查通过，保留三条全退及一条未曝光关闭历史审核，不清投影；七服务健康open/READY，当前无活动告警。B/网关及维护工具已更新指纹，A冻结镜像不变；Linux和B06.5～.7未验。


### B-06.5 单机故障与恢复（Windows Docker已验收）

方案和恢复命令见[故障恢复手册](FAULT-RECOVERY.md)。最终07的112项真实故障/资金库存/名额检查及两项独立中断恢复（NameServer recovery-03、B缺失runtime-gap-02）通过；111项JUnit、33项镜像、9项维护、9项故障工具回归通过。D44仅修正只读观测的历史交接分类，3项关系测试（30反例）及7项原观测回归、真实MySQL查询通过，原记录保留。当前七服务open/READY，无活动告警、逆操作日志为空。最新发布docs/b06-fault-release.json、验收docs/tests/b06-fault-acceptance.json、过程15.3～15.4；B06全部成果未提交/合并/推送。Linux、备份恢复和发布回滚留待后续阶段。


### B-06.6 备份恢复与发布回滚（Windows Docker已验收）

操作见[备份恢复与发布回退手册](BACKUP-RECOVERY.md)。支持完整停写冷备、完成标记/hash核验、从已封存备份恢复到新项目/空卷/独立网络、同批中断recover；原卷保留。02/03/04分别40/39/11项实际检查、16项保护及1项真实ACL回归、12实际权限范围通过。真实原签名消息重复消费幂等、恢复后新未付购买/checkout/取消、不同镜像ID兼容包装发布/失败关闭入口/原ID回退已验证，schema不降级。最终原七服务open/READY，无活动告警和未完成逆操作；档案/恢复卷保留，秘密仅本机私有ACL保护且未加密。回退范围限相同已验业务jar的发布包装，不认证未知旧业务版本。证据docs/tests/b06-backup-acceptance.json、发布docs/b06-backup-release.json、过程16.3及路线图25.16；下一步B-06.7，Linux/异机/断电/PITR未验，Git未提交或推送。


## B-06.7 最终交付入口

[DELIVERY.md](DELIVERY.md)提供现有运行/维护/停止、首次初始化、浏览器演示、备份/回退、中断恢复、公开/私有材料及Linux待验清单。最终候选docs/b06-final-release.json、最终24浏览器/11守恒/40恢复证据docs/tests/b06-final-acceptance.json、公开包索引docs/b06-delivery-manifest.json配套；公开ZIP逐文件hash/COMPLETE封存，实际秘密及约3.93GB冷备独立保管。全部未Git发布，Linux未验。
