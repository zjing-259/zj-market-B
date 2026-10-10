# B-02开发过程：用户、商品与商城浏览

> 历史状态说明（2026-10-10）：本文保留各实施时点的工作树、分支、未提交/未合并/未推送状态、验收批次和产物指纹；这些记录不代表当前 Git 状态。B-02、目录整理与补修、B-03及D6收尾均已包含在 `7cef241`；当前接续工作树为 `D:/Java/zj-market-b-04`，分支 `b-04`。最新进度见 [B-04开发过程](b04-development.md)及[路线图](development-roadmap.md)。历史 `.local`、`target` 和前端依赖不随 Git 复制，旧报告不作为新工作树重新验收的证据。

更新：2026-10-09。阶段入口：[开发路线图第8节](development-roadmap.md)。
本文件是B-02唯一的开发过程记录；设计、选择、实现进度、复现命令、证据及遗留事项都在此维护。B-03及以后开始时分别建立对应过程文档，不补建B-01过程文档。

## 1. 当前状态与记录规则

B-02.1已完成（设计确认）：范围、领域模型、登录/前端方案和HTTP接口成文，D1～D6关键方案均已获用户选择。B-02.2已完成（实际验收）：身份HTTP、用户/运营权限、页面交互、正式类型/生产构建和一键浏览器入口通过，D9按用户选择固定TypeScript6.0.3。B-02.3已完成（实际验收）：商品主数据、统一版本、原子事件保存及真实HTTP/浏览器通过，D12按用户选择对齐A的128个UTF-16单元上限；B-02.4已完成（实际验收）：可靠发布与签名结果确认、持久Inbox/进度、补查/受控恢复、隔离维护及真实故障/页面联调通过；B-02.5已完成真实A试算、商城页面及受影响回归，见第14节；B-02.6联合验收及交接已完成，第15节本轮报告全部通过；B-02身份—商品—同步—试算—浏览闭环已验收，不代表交易或生产上线。

| 小阶段 | 状态 | 交付与验收入口 |
| --- | --- | --- |
| B-02.1 范围、模型与接口设计 | 已完成（设计确认） | 本文第2～9节及[HTTP契约](b02-http-api.json)；完成条件见第10节 |
| B-02.2 身份与权限 | 已完成（实际验收） | 注册/登录/刷新/退出/身份/用户与运营权限、正式前端构建及一键浏览器验收通过，见第11节 |
| B-02.3 商品与原子事件 | 已完成（实际验收） | 商品维护/浏览、版本并发、商品和Outbox同事务；见第12节 |
| B-02.4 可靠同步闭环 | 已完成（实际验收） | 可靠发布/租约、签名结果/Inbox、补查/暂停恢复、隔离维护、真实A/B故障及页面；见第13节 |
| B-02.5 试算与商城页面 | 已完成 | 真实A试算与前端展示，不提供虚假下单/支付 |
| B-02.6 联合验收与交接 | 已完成（实际联合验收及交接） | 真实前后端/A故障验收、迁移权限、B-03交接 |

每次小阶段变更记录日期、实际改动、用户选择、测试命令与结果、剩余项。只有真实运行证据才能标记功能验收通过；设计契约可先完成，但不代表接口已部署。阶段文档末尾始终维护本次复杂度；后续阶段开始时创建docs/b03-development.md等，不预建空文档。

B-02 已归档：业务提交 `9d75f82`，文档归档 `dd59938`，目录整理 `d9f12c7`，补修 `f93c861`，主分支归档 `36dbc6b`；均已包含在 B-03交付提交 `7cef241`。当前接续工作树为 `D:/Java/zj-market-b-04`、分支 `b-04`。原目录与各实施工作树分置、未提交/未合并等描述属于第10～18节的历史过程；当前目录规范见 [project-layout.md](project-layout.md)，后续过程见 [B-04开发过程](b04-development.md)。

## 2. 用户选择与范围

| 编号 | 用户选择 | 影响 |
| --- | --- | --- |
| D1 | JWT＋开放注册＋短期访问JWT与可轮换刷新令牌 | 增加普通用户注册；需要刷新、撤销及持久登录记录，不采用Session登录方案 |
| D2 | Vue 3＋TypeScript＋Vite | 前端拟放工作树frontend/；商城与简易商品管理同一工程 |
| D3 | 匿名浏览在售商品，登录后试算；简易商品管理页；外部HTTPS图片地址 | 不实现上传/对象存储；商品页面不展示MQ等实现细节 |
| D4 | MyBatis＋显式事务 | Mapper归基础设施；商品、完整Outbox及同步目标本地原子保存 |
| D5 | 所有有效编辑递增同一商品版本 | 改图片/描述也产生新版本与快照；不维护第二套编辑版本 |
| D6 | RS256公私钥签名 | 签名密钥与A/B RPC/MQ签名密钥分离，外部注入 |
| D7 | Argon2id | 密码12～64 Unicode字符；实际性能及参数见第11节 |
| D8 | 进程内限流，首版单实例 | 限制IP与登录名，容量有上限；多实例需重新确认共享方案 |
| D9 | 固定TypeScript6.0.3 | 保留Vue3/Vite/vue-tsc，更新锁文件并通过正式类型及生产构建 |
| D10 | 名称去首尾空白、描述保留原文 | 按规范化后的全部字段比较是否有效编辑；描述空白和换行原样保存 |
| D11 | 检测到HTML标签就拒绝 | 不自动去标签改写内容；页面提示使用纯文本并用Vue文本插值渲染 |
| D12 | B沿用A的128个UTF-16单元上限，emoji通常占2个 | 后端String.length、前端JS字符串长度和页面提示一致；边界实测通过，A无须调整 |
| D13 | 生产发送退避1／2／4／8分钟；隔离验收用2～8秒加速 | 扫描2秒、认领租约30秒、每轮最多20条、结果补查30秒；加速只允许独立B测试库 |
| D14 | 5次告警后继续按8分钟上限自动重试，运营可暂停／恢复 | 确定业务拒绝或证据矛盾停止重投；已发布但长期缺结果先补查，再受控重投原事件；覆盖最初“10次后暂停”的选择 |
| D15 | 毒消息持久隔离；运营页面只查脱敏记录，重放走受控维护入口 | 隔离成功后确认消费，保存失败则重试；修复配置后重放仍须验签，不允许改正文或绕过验签 |
| D16 | 业务组最多重新消费8次 | 超限进入死信；B保留待核对状态并用queryEventResult补查，独立测试组加速验收不改变业务策略 |
| D17 | 登录后进入商品详情自动试算，提供“重新试算” | 仅调用真实A，不缓存结果；商品版本或登录身份变化清除旧结果 |
| D18 | 每3秒刷新B商品资料，最多1分钟；之后可手动刷新 | 未确认同步前不调用A试算，确认后恢复自动试算；到期停止自动读取 |
| D19 | 对齐A模块边界，增加api/types、业务服务归domain、移除application | 依赖与配置装配调整；保留独立verification |
| D20 | 现有业务服务建立I*Service，实现放独立子目录 | 四个业务服务及依赖方使用接口；模型、DAO和适配实现分类 |
| D21 | 退出同时撤销JWT与刷新Cookie各自对应的登录，再清Cookie | 同一登录去重；不同登录按稳定顺序、同事务撤销；不撤销未提供凭据的其他登录 |

包含：普通用户注册/登录/退出/刷新、本人查询、最小USER/OPERATOR权限、商品创建/编辑/上下架、列表/详情、可靠同步及异常查询/受控重试、优惠试算、商城与简易商品管理页面。
不包含：订单、库存预留/扣减、A占位、支付/退款、履约、购物车、多SKU合单、普通购买、复杂运营后台、社交登录、找回密码、邮箱/短信验证、图片上传。注册不自动登录；注册成功后进入登录页面。学习环境的运营账号通过受控初始化建立，注册接口不能创建运营角色。

## 3. 领域模型与不变条件

业务术语以[CONTEXT.md](../CONTEXT.md)为准，模型不直接使用A DTO或数据库实体。

| 聚合或模型 | 标识与核心字段 | 不变条件 |
| --- | --- | --- |
| 商城用户User | userId、loginName、displayName、status、roles、authVersion | userId稳定且与登录名分离；登录名唯一；注册固定USER；禁用或认证版本变化使既有登录失效 |
| 商品Product（首版单SKU） | goodsId、goodsName、description、imageUrl、originalPrice、currency、saleStatus、productVersion | goodsId就是提供给A的SKU标识，不另建重复映射；创建版本1；所有有效编辑递增；同版本营销快照不可变 |
| 营销快照ProductSnapshot | goodsId、productVersion、goodsName、originalPrice、currency、saleStatus | 严格对应A既有全量快照，不包含图片/描述或库存；与商品提交同事务写入完整事件正文 |
| 同步进度ProductSyncProgress | 当前目标版本/事件、已确认版本、状态、最近错误/核对时间 | 业务商品版本和同步确认分开；旧回执只能更新历史记录，不能使新版本变成已确认 |
| 登录记录LoginGrant | grantId、userId、authVersion、过期时间、撤销状态、刷新令牌摘要/轮换链 | 属于用户访问的持久登录凭据，不是商城订单；退出撤销当前登录，禁用用户使全部登录不可用 |

userId/goodsId/事件ID由B服务端生成，采用不透明字符串，至多64字符、无首尾空白、精确匹配；HTTP不接受浏览器分配可信userId/goodsId。具体生成器在编码时落实，但不能依赖登录名或可变展示名称。首版loginName约束为3～32位小写ASCII字母、数字、点、下划线、短横线，首位字母或数字；不静默trim或改变大小写。标识和登录名列使用精确比较语义及唯一索引，避免默认数据库排序规则改变身份匹配。

displayName为1～64字符；goodsName按D12去掉首尾空白后为1～128个UTF-16单元，普通中文占1个、emoji通常占2个，与A实际校验一致；description为至多2000字符的纯文本。imageUrl允许null或至多2048字符的HTTPS地址；B不抓取远程图片，前端使用图片元素并提供失败占位。客户端不得提交HTML作为描述，不以v-html直接渲染。

金额使用精确十进制值，HTTP/MQ为两位小数字符串；CNY，原价0.01～999999.99，不接受额外精度和隐式舍入。版本为1～9223372036854775807的无前导零十进制字符串，前端不能转JS Number。UTC时间采用ISO-8601毫秒表示。

商品创建默认OFF_SALE，未提供description/imageUrl时分别为纯文本空串/null。修改使用expectedVersion比较并更新，单条受影响记录才能递增版本；失败返回409 PRODUCT_EDIT_CONFLICT，不覆盖他人编辑。所有归一化后相同的字段视为无变化，返回原版本且不新建事件；版本溢出拒绝，不循环归零。图片/描述变更虽然不改变营销字段，仍递增版本并产生同营销内容的新版本快照，这是D5明确选择的简化规则。

同步状态为PENDING、CONFIRMED、REJECTED、RECONCILIATION_REQUIRED。CONFIRMED须由可信持久结果证明当前目标事件的版本已被A认可；SEND_OK不够。APPLIED需关联事件/商品/版本匹配；IGNORED且currentVersion等于目标版本可确认同一快照，较小/较大或矛盾证据进入核对，不能一律确认。更旧事件的结果不能回退商品或覆盖新目标；REJECTED保留原因供运营修正，新编辑生成新版本，不能无限重投同版本异内容。

匿名可见范围仅ON_SALE；下架立即影响B列表/详情和新试算，不能等待MQ。同步未确认时可浏览基础资料，显示“资料更新中，暂不可试算”；尚无下单接口，不能显示库存可售承诺或可完成购买的按钮。

## 4. 登录、令牌与权限设计

访问JWT初始有效15分钟（可配置）；刷新登录绝对寿命7天，不因刷新无限延长。参数外部配置，并在B-02.2实际测试短周期过期。JWT只接受RS256，使用kid与外部可信RSA密钥；密钥路径与issuer/audience外部注入，签名私钥不进入仓库或前端。RSA密钥至少2048位，保留旧验签公钥覆盖尚未过期访问JWT；不得接受token指定的任意alg、jku或远程密钥地址。校验issuer、audience、sub、sid、jti、iat/nbf/exp，时钟偏差上限30秒。JWT不包含密码或令牌摘要，用户/角色以服务端当前记录为准。实际B通过AccessTokenPort封装Spring Security引用的Nimbus JOSE/JWT库，固定RS256与可信本地公钥并显式校验声明和时钟；底层机制依据见[官方JWT说明](https://docs.spring.io/spring-security/reference/servlet/oauth2/resource-server/jwt.html)。

访问JWT只保存在前端内存，以Authorization: Bearer发送；不写localStorage/sessionStorage或URL。刷新令牌是不透明随机值，只用HttpOnly、Secure、SameSite=Lax、Host-only cookie B_REFRESH传递，Path=/api/v1/auth。生产HTTPS；本机HTTP仅以显式开发配置允许Secure=false。刷新令牌不出现在JSON、日志或前端状态中，数据库仅保存摘要。

每次刷新在本地事务中锁定登录记录，旧令牌置为已使用、生成替代令牌并保留轮换链；旧令牌再次使用则撤销该登录的整个轮换链。数据库提交后才能发出新JWT与cookie。若提交成功但响应丢失，客户端不得重放旧刷新令牌，重新登录；这是明确的安全失败处理，不伪装刷新成功。轮换与重用检测参考[RFC9700第4.14节](https://www.rfc-editor.org/rfc/rfc9700.html#section-4.14)，这里借鉴保护措施，不声称实现完整OAuth授权服务器。

同一浏览器的刷新请求需要串行，前端实现单次刷新队列，并协调多标签页，不能以无限重试处理401；受保护读请求最多刷新后重试一次，商品写请求不能在不确定提交结果时自动重发。页面重载时通过刷新接口恢复内存访问JWT。

JWT验签之后，每个受保护请求还检查登录grant未撤销/未过期、用户启用及authVersion一致，授权从当前角色取得；因此退出可立即阻止该登录后续请求，禁用可立即拒绝所有旧JWT。本设计有服务端撤销状态，不把“JWT尚未过期”等同“登录仍有效”。认证库不可用返回503，不允许放行；登录状态检查与业务执行之间已进入的事务按自身提交边界处理，不声称撤销能回滚在途事务。

注册、登录、刷新、退出通过同源Origin/Referer约束及CSRF令牌保护。GET /auth/csrf取得CSRF token，浏览器在上述POST中发送X-CSRF-TOKEN；登录/刷新/退出后重新取得token。普通资源操作只接受Bearer访问JWT，不把刷新cookie当资源认证。关闭跨域通配允许，开发使用Vite代理、部署同源反向代理；不能因JWT登录就关闭cookie端点的CSRF，参考[Spring CSRF说明](https://docs.spring.io/spring-security/reference/servlet/exploits/csrf.html)。

密码使用框架PasswordEncoder的安全单向摘要与独立盐，不写明文或可逆密码；D7由用户选择Argon2id，参数及实测见第11节。[Spring密码存储说明](https://docs.spring.io/spring-security/reference/features/authentication/password-storage.html)仅作为机制依据，不等于B已完成验收。密码长度12～64 Unicode字符，不trim、不日志化，所选编码器若存在字节长度限制必须显式校验并同步HTTP契约。

注册/登录限流按受控客户端地址及登录名设置可配置阈值；地址不直接信任任意X-Forwarded-For。登录名不存在/密码错误/禁用统一返回401 INVALID_CREDENTIALS，不泄露原因；注册已占用返回409 LOGIN_NAME_UNAVAILABLE。公开注册拒绝roles、status、authVersion、userId等附加身份字段。运营初始化凭据外部注入，启动不隐式创建或覆盖账号。

## 5. 用例、权限、事务与失败处理

| 用例 | 权限 | 本地边界 | 失败处理 |
| --- | --- | --- | --- |
| 注册 | 匿名＋CSRF＋限流 | 写User、密码摘要及USER角色，同事务；唯一登录名约束 | 参数400；名称占用409；不自动登录、不创建运营 |
| 登录 | 匿名＋CSRF＋限流 | 凭据验证后新建登录grant及刷新链；事务内准备令牌，提交后才发出 | 错误401；库/签名配置异常503；不返回部分令牌 |
| 刷新 | 有效刷新cookie＋CSRF | 锁定并轮换刷新链，核验当前用户状态，事务内准备令牌、提交后发出；检测重用时先提交撤销再返回401 | 无效/过期/重用401；重用撤销当前链；不能重放旧令牌 |
| 退出 | 当前可信JWT与/或刷新cookie＋CSRF | 撤销两份凭据分别对应的grant（同一grant只一次），保留必要重用记录 | 重复退出幂等成功；清cookie；库不可用503不能宣称已撤销 |
| 本人查询 | 有效访问JWT | 读取当前User与角色 | 401拒绝；不接受目标userId参数 |
| 公共商品列表/详情 | 匿名允许 | 只读B当前商品及浏览可用状态 | 下架/不存在404；DB故障503；不调用A获取列表 |
| 商品创建/编辑 | OPERATOR | 商品＋版本＋完整Outbox正文＋同步目标一次提交 | 参数400；并发409；回滚均不落库；A离线不阻塞本地提交 |
| 同步状态/受控重试 | OPERATOR | 状态只读；重试锁定原事件并排队，不改正文或eventId | 不存在404；不可重试状态409；技术故障503 |
| 优惠试算 | 有效访问JWT；USER或OPERATOR | 读取当前在售且已确认版本，离开本地事务后调用A；回读确认版本未变化 | 同步未就绪或RPC版本冲突409；超时504；依赖不可用503；绝不返回过时优惠 |

商品更新结果未知时，前端重新读取商品并比较版本/字段，不按新业务键自动重发。可靠同步的租约、退避与补查周期在B-02.4确认，不把未确定参数写成现有能力。

## 6. HTTP接口设计

接口前缀/api/v1，JSON UTF-8。详细字段、请求限制及权限见[b02-http-api.json](b02-http-api.json)。身份接口及6个商品操作已在实际B实现并验收；商品名称边界按D12收口，独立同步管理已在.4完成；试算操作正在.5实现，机器文档逐操作标明implemented/planned。

| 方法/路径（省略/api/v1） | 权限及关键请求 | 返回/特殊错误 | 实现阶段 |
| --- | --- | --- | --- |
| GET /auth/csrf | 同源匿名 | CSRF token/headerName，Cache-Control:no-store | .2 |
| POST /auth/register | 匿名＋CSRF；loginName/password/displayName | 201 User；400/409/429 | .2 |
| POST /auth/login | 匿名＋CSRF；loginName/password | JWT/user/expiresIn＋刷新cookie；401/429 | .2 |
| POST /auth/refresh | 刷新cookie＋CSRF；空正文 | 新JWT及轮换刷新cookie；401/503 | .2 |
| POST /auth/logout | 当前登录＋CSRF；空正文 | 幂等成功、清cookie；无登录可成功 | .2 |
| GET /users/me | 访问JWT | 本人User；不接收query参数，401/400 | .2 |
| GET /admin/users/me | OPERATOR访问JWT | 当前本人运营身份；401/403，作为真实运营权限检查入口 | .2 |
| GET /products | 匿名；page/size | 只含在售商品的分页基础资料 | .3 |
| GET /products/{goodsId} | 匿名 | 在售详情；404 | .3 |
| POST /products/{goodsId}/trial | 访问JWT；空正文 | 优惠估算；409/503/504 | .5 |
| GET /admin/products | OPERATOR；分页/可选saleStatus | 包括下架的管理列表 | .3 |
| GET /admin/products/{goodsId} | OPERATOR | 完整管理详情 | .3 |
| POST /admin/products | OPERATOR；商品字段，默认OFF_SALE | 201商品及PENDING同步；本地提交已完成 | .3 |
| PUT /admin/products/{goodsId} | OPERATOR；完整商品字段＋expectedVersion | 新版本/无变化原版本；409 | .3 |
| GET /admin/products/{goodsId}/sync | OPERATOR | 目标/确认版本、原事件、状态、脱敏失败原因 | .4 |
| POST /admin/products/{goodsId}/sync/retries | OPERATOR；原eventId＋expectedVersion | 202已排队（不是A已处理）；409；依赖异常502/503 | .4 |
| POST /admin/products/{goodsId}/sync/pauses | OPERATOR；当前原eventId＋expectedVersion | 200暂停状态；409 | .4 |
| GET /admin/sync/quarantine | OPERATOR；page/size | 200仅六项脱敏元数据，不返回正文/签名/密钥 | .4 |

商品状态修改包含在PUT中，不再设置另一个无版本校验的上下架入口；不提供删除商品接口。浏览页的“试算”请求不接受userId、价格、商品版本、source/channel、quantity或activityId；B从登录上下文和当前商品提供这些值，quantity固定1、activityId不指定，由A选择。

统一响应为{code,message,data,requestId}，成功code=0000；失败data=null，可附fieldErrors。HTTP状态与业务码同时有效，不把失败全部包装成200。requestId由B生成，响应头X-Request-Id及结构字段一致，转为RPC关联ID；日志关联eventId/grantId但不输出令牌、密码和消息敏感正文。时间和金额/版本遵守第3节格式。

400 VALIDATION_FAILED、401 AUTH_REQUIRED/TOKEN_INVALID/TOKEN_EXPIRED/INVALID_CREDENTIALS、403 FORBIDDEN/CSRF_INVALID、404 PRODUCT_NOT_FOUND、409 LOGIN_NAME_UNAVAILABLE/PRODUCT_EDIT_CONFLICT/PRODUCT_VERSION_EXHAUSTED/PRODUCT_SYNC_PENDING/PRODUCT_VERSION_MISMATCH/RETRY_NOT_ALLOWED、429 RATE_LIMITED、502 UPSTREAM_RESPONSE_INVALID/INTEGRATION_AUTH_FAILED、503 DEPENDENCY_UNAVAILABLE、504 UPSTREAM_TIMEOUT、500 INTERNAL_ERROR。若A认证错误，它是B上游配置故障，不能映射成浏览器用户登录401。

试算输出为goodsId/productVersion/quotedAt/state/offer，state为AVAILABLE、INELIGIBLE或NO_PUBLIC_OFFER。先校验A三个布尔字段完整；!visible或!available映射为NO_PUBLIC_OFFER、offer=null，不能披露隐藏活动ID/专属原因；其余!eligible为INELIGIBLE，只有符合可见性约束的公开offer才可返回；其余为AVAILABLE且offer必须完整。A的技术异常不得伪装为NO_PUBLIC_OFFER。

offer仅映射activityId、goodsId、productVersion、originalPrice、deductionPrice、payPrice、currency、targetCount；验金额关系、范围、商品与版本一致，异常502；不透传A DTO或原始异常。试算返回不保价，不产生订单/库存/占位。响应Cache-Control:no-store。

## 7. 前端页面与接入顺序

Vue 3＋TypeScript＋Vite是用户已选方案；[Vue官方脚手架说明](https://vuejs.org/guide/quick-start.html)支持Vite和TypeScript。新增依赖精确版本及锁文件在建立前端骨架时记录，当前已建立frontend骨架、登录/注册/身份页、同源代理及锁文件，真实浏览器流程通过；D9已选择并固定TypeScript6.0.3，正式类型/生产构建及一键入口通过。

| 页面 | 交互与接入 |
| --- | --- |
| /login、/register | 表单、明确错误、注册后登录；返回地址只允许站内路径 |
| /、/products | 匿名浏览在售列表与基础价，不调用匿名优惠试算 |
| /products/:goodsId | 当前基础资料；未登录提示登录试算；同步中/无公开优惠/资格不符/上游异常分别展示；没有下单或支付按钮 |
| /admin/products | 运营列表、创建/编辑/上下架及版本冲突提示；普通用户服务端403 |
| /admin/products/:goodsId/sync | 运营同步状态和受控重试；只在管理页显示同步技术细节 |

共用HTTP客户端维护内存JWT、CSRF、刷新队列、requestId与错误映射。路由守卫只是交互辅助，服务端仍鉴权。生产同源，开发代理/api至B；默认不开放跨域凭据。页面按.2身份、.3商品、.4管理同步、.5真实试算逐步接入；mock仅用于开发显示，不能作为验收。

## 8. 持久化、迁移与模块落点

MyBatis Mapper/映射实体放infrastructure，领域和应用不依赖MyBatis/Spring。应用定义UserRepository、ProductRepository、ProductSyncRepository、OutboxRepository、LoginGrantRepository、MarketingTrialPort及UnitOfWork端口；基础设施用同一B DataSource和显式事务实现UnitOfWork，装配放app。HTTP转换放trigger；MQ SDK解码/验签在infrastructure后调用应用端口，不打破trigger禁止A SDK的规则。

MyBatis候选4.1.x，官方[4.1.0发布](https://github.com/mybatis/spring-boot-starter/releases)和[支持说明](https://github.com/mybatis/spring-boot-starter/blob/master/README.md)对应Boot4.1。B-02.2已用Boot4.1.1/JDK21实际打包并验证Mapper、显式事务回滚及依赖树，复跑Netty/JSON固定组合的RPC/MQ/签名链路；没有升降Boot。

这里只确定逻辑数据职责：用户/角色与凭据、登录grant与刷新轮换链、商品、不可变Outbox、Inbox去重及事件处理记录、商品同步目标/确认。身份SQL已由V2显式迁移交付；商品/事件SQL仍留待.3/.4，不创建订单/库存/支付表。

Flyway显式执行，普通启动不迁移；迁移账号与运行账号隔离，新增业务表逐表授予必要运行DML，历史表不可写。测试使用独立zj_market_b02_test等B schema与测试账号，启动/验收入口须拒绝A库、开发库与缺失测试配置；本轮已建立并验证固定zj_market_b02_test与独立账号，具体入口及负向防误用见第11节；开发库zj_market亦已显式迁移身份表并逐表授权。

## 9. 测试矩阵与具体边缘场景

| 场景 | 预期及后续阶段 |
| --- | --- |
| 注册重复登录名/附加OPERATOR角色/格式大小写 | 唯一约束冲突409；附加身份字段400；不创建运营，.2 |
| 登录错误、伪造JWT、过期、错误issuer/audience/算法 | 拒绝且不泄露凭据，.2 |
| 刷新轮换、旧token重用、并发刷新、响应丢失 | 原子轮换；重用撤销当前链；需要重新登录的情况明确，.2 |
| 退出后未过期JWT、禁用后全部旧JWT、认证库断开 | 拒绝既有登录；库不可用503，不放行，.2 |
| 普通用户管理请求、浏览器伪造userId或价格 | 服务端403/400；A请求使用可信上下文，.2/.5 |
| 两运营同时编辑v5 | 仅一方成功v6，另一方409，不产生重复v6，.3 |
| 图片/描述编辑与无变化编辑 | 前者递增并生成新事件；后者版本与事件不变，.3 |
| 商品事务写Outbox失败或A离线 | 回滚商品和事件；A离线仍本地提交PENDING，.3 |
| v7回执先到v6后到；A忽略旧事件 | 不回退商品或当前同步确认，.4 |
| 相同版本异正文、重复结果、消费后未ACK | 冲突受控修正；Inbox与进度同事务；重复无额外效果，.4 |
| 查询NOT_FOUND/WAITING_DEPENDENCY、结果丢失、发布确认丢失 | 不宣布完成/拒绝，补查与原事件恢复，.4 |
| 本地v7试算期间编辑v8或下架 | 回读失败409，不向页面返回v7优惠，.5 |
| 无活动/不可见/不具资格/A超时或认证配置故障 | 隐藏详情不泄露；故障不伪装无活动，.5 |
| JS大版本、非法金额、图片失败、前端刷新/返回 | 字符串精度与明确占位/错误状态，.3/.5 |

B-03交接字段：可信userId、稳定goodsId、当前productVersion、原价/币种、可见试算的活动/折扣/应付及quotedAt；下单必须重新校验，不承诺试算保价或库存。

## 10. B-02.1完成条件与过程记录

- 用户选项D1～D6全部有明确答案。
- 用户/商品聚合、标识、单版本、同步确认和用例权限/事务/失败设计成文；无已发现而未解决的A接口差异。
- 登录/前端方案及HTTP请求/响应/错误形成可复查契约；机器契约结构与内部引用检查通过。
- 迁移/运行权限、后续测试矩阵与B-01前置限制注明；只标记设计任务完成，不标记功能上线。

2026-10-08：B-02.1设计确认完成。承接已有B-01基线，核对路线图第8节、A契约TrialRequest/TrialResponse/Offer/ProductSnapshotChanged和模块依赖。D1～D6按用户答案确认，其中D6为RS256。建立本阶段唯一过程文档与HTTP契约。结构检查15操作、38数据模型、267内部引用通过，并检查注册不能提交运营角色、试算不能提交身份/价格/版本、编辑必须带expectedVersion。没有全量OpenAPI第三方校验或真实接口测试；当前只实施文档/词汇，不执行业务迁移。

## 11. B-02.2 实施过程（2026-10-08）

状态：B-02.2已完成（实际验收），包括身份后端、页面真实交互、正式类型/生产构建及一键验收入口。代码落在 `D:/Java/zj-market-b01`，本文件为B-02唯一过程记录。

### 11.1 选择与拆分

D7：用户选择Argon2id；D8：用户选择进程内限流、首版单实例。D9：初始TypeScript7.0.2无法被vue-tsc3.3.12加载（ERR_PACKAGE_PATH_NOT_EXPORTED，typescript/lib/tsc）；2026-10-08用户明确选择固定TypeScript6.0.3。已同步package.json及package-lock.json，正式npm ci、npm run build（vue-tsc＋Vite）与run-b02-browser.ps1全部通过，未升降Java或Boot。前期临时兼容探针仅是选项证据，最终完成依据为本轮正式入口。

| 步骤 | 目标 | 依赖 | 实际结果 |
| --- | --- | --- | --- |
| .2-a 身份持久化 | User、角色、登录grant、刷新摘要与迁移 | MyBatis4.1.0、独立B测试库 | 实际Mapper/回滚、开发及测试库逐表DML、跨库/DDL拒绝通过 |
| .2-b 认证与权限 | RS256、刷新轮换、退出撤销、当前用户权限 | .2-a、外部独立RSA密钥 | 实际HTTP及15项Maven测试通过 |
| .2-c 页面与启动入口 | Vue登录注册、内存JWT、同源代理、受控运营初始化 | .2-b | Edge真实页面及运营CLI、npm ci、正式类型/生产构建通过 |
| .2-d 综合复验 | 入口、原基线、文档与证据 | 前三步 | 普通Web404、JDK21、RPC/MQ/签名及数据库通过；正式一键浏览器入口与进程/环境恢复通过 |

### 11.2 实现边界与实际版本

- domain为User/LoginGrant/RefreshCredential；application为IdentityService及IdentityStore/PasswordPort/AccessTokenPort，不引用Spring/MyBatis。基础设施实现Mapper、密码摘要、JWT；trigger只转换HTTP；app装配HTTP身份过滤、错误映射和浏览器CSRF/限流。
- 四张身份表：b_user、b_user_role、b_login_grant、b_refresh_token。userId/loginName使用ascii_bin及唯一约束；密码仅保存带算法前缀的Argon2摘要，刷新凭据仅保存SHA-256摘要。未创建商品、订单、库存、支付表。
- 显式TransactionTemplate＋READ_COMMITTED；Mapper本地缓存STATEMENT。刷新按user→grant锁顺序重查，已用旧token的重用先提交撤销再返回401；签名失败和普通事务失败均回滚。绝对刷新期限保持不变；退出撤销后续JWT，禁用/authVersion及角色变化即时参与请求校验。
- JWT默认900秒，最长900秒；刷新默认604800秒，最长604800秒，非滑动续期。kid映射本地公钥允许列表，支持保留旧公钥；不使用令牌中的远程密钥地址。生产默认Secure cookie且要求HTTPS origin；仅明确loopback开发配置允许Secure=false。
- Argon2id：19MiB、迭代2、并行度1、16字节随机盐、32字节输出，符合[OWASP参数基线](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)。目标JDK实测单次耗时写入target/identity/verify.txt；不是负载压测或QPS承诺。64个Unicode码点密码验收通过，没有BCrypt字节上限。
- 注册/登录同源Origin或Referer＋CSRF；B_CSRF为HttpOnly/同路径cookie，GET接口取token，认证成功后更新cookie。前端Web Locks串行化各标签的cookie变更，同标签刷新单飞，BroadcastChannel传播退出；不支持Web Locks时明确拒绝登录，不回退为有重用风险的无锁刷新。Bearer资源不使用刷新cookie鉴权。
- 限流默认每socket IP每60秒20次、每loginName每60秒5次，注册与登录共享计数；上限10000桶，返回429/Retry-After。B_IDENTITY_RATE_IP_LIMIT/LOGIN_LIMIT/WINDOW_SECONDS外部可调。只信任实际socket IP，不采信任意X-Forwarded-For；首版单实例，代理或多实例共享边界留待专门选择。
- 无默认Spring账号、无启动自动建表或运营账号。运营只能通过显式CLI初始化；已存在loginName拒绝，不覆盖密码或自动给已有用户提权。

实际依赖：JDK21.0.2、Boot4.1.1、Spring7.0.9、Security7.1.1、MyBatis starter/MyBatis-Spring4.1.0、MyBatis3.5.19、Nimbus10.9.1、BouncyCastle1.86、Flyway12.4.0、MySQL8.0.32。Netty4.1.118.Final、Dubbo3.2.16、RocketMQ4.9.7、签名Jackson2.21.5及HTTP Jackson3.1.5保持；依赖树见各模块target/b02-dependencies.txt。

前端当前锁定Vue3.5.43、Vite8.3.3、plugin-vue6.0.9、vue-tsc3.3.12，Node24.16.0/npm11.13.0；TypeScript6.0.3按D9固定，锁文件已同步。正式类型检查和生产构建通过；未用浏览器运行代替类型检查。

### 11.3 复现入口

以下命令从PowerShell7在工作树执行；数据库凭据由忽略的Windows DPAPI文件或外部环境注入，RSA路径由外部配置注入。不要打印凭据文件或密码环境变量。

```powershell
Set-Location D:/Java/zj-market-b01
# 显式JDK21构建，包含原8项及新增7项RSA测试
./scripts/mvn.ps1 -MavenArguments @('-B','-pl','zj-market-verification','-am','package')
# 独立测试库/账号、显式迁移、运行权限、真实身份HTTP验收和测试RSA密钥
./docs/tests/run-b02-identity.ps1 -SkipBuild
# B开发库显式迁移及逐表运行权限；不会自动创建学习运营账号
./scripts/provision-b-database.ps1 -SkipBuild
# 正式浏览器入口：包含npm ci/type build、实际身份HTTP、运营初始化和进程清理
./docs/tests/run-b02-browser.ps1 -SkipBuild
# 原RPC/MQ/TLS/签名复验（A独立验收库；不改A开发库）
./docs/tests/run-b01-environment.ps1 -SkipBuild -RunName b022-20261008
```

测试入口只能使用精确zj_market_b02_test、zj_market_b02_test_app及显式b02-test scope；使用开发库凭据文件执行identity verify实测被拒绝。迁移账号不进入普通B或身份HTTP子进程；普通启动也移除运营初始化环境变量。测试随机账号保留在隔离测试库，不清理或重置A数据。

身份启动示例使用已由验收入口生成的**测试**RSA密钥，不能把此例当生产密钥配置：

```powershell
$env:B_IDENTITY_ORIGIN='http://127.0.0.1:5173'
$env:B_IDENTITY_SECURE_COOKIES='false'
$env:B_IDENTITY_KEY_ID='b02-test'
$env:B_IDENTITY_PRIVATE_KEY_FILE='D:/Java/zj-market-b01/.local/b02-test-keys/private.pem'
$env:B_IDENTITY_PUBLIC_KEY_FILE='D:/Java/zj-market-b01/.local/b02-test-keys/public.pem'
./scripts/start-identity.ps1 -TestDatabase -SkipBuild
# 另一个终端：cd D:/Java/zj-market-b01/frontend; npm run dev
```

普通开发启动省略-TestDatabase，默认使用.local/database.credentials.xml；部署使用自己的HTTPS origin、公私钥和运行凭据，默认不关闭Secure。所有Java入口复用b-runtime.ps1选择JDK21，不改变终端/A的Java8；普通app不含Flyway/验收程序。

运营初始化使用自己的目标库/密钥配置和外部账号数据，密码通过交互读取而不是写进命令历史：

```powershell
$env:B_OPERATOR_LOGIN_NAME='market_operator'
$env:B_OPERATOR_DISPLAY_NAME='商城运营'
$secret=Read-Host '运营密码（12～64字符）' -AsSecureString
try {
  $env:B_OPERATOR_PASSWORD=[Net.NetworkCredential]::new('', $secret).Password
  ./scripts/identity.ps1 -Mode init-operator -SkipBuild
} finally {
  foreach($name in @('B_OPERATOR_LOGIN_NAME','B_OPERATOR_DISPLAY_NAME','B_OPERATOR_PASSWORD')) {
    [Environment]::SetEnvironmentVariable($name,$null,'Process')
  }
}
```

### 11.4 证据、剩余项与范围

| 检查 | 实際证据（工作树、忽略目录） | 结果 |
| --- | --- | --- |
| 构建/原8项＋RSA7项 | target/b02-package.txt；各模块surefire-reports | 15项通过 |
| 实际HTTP身份/事务 | target/identity/verify.txt、target/b02-identity-run.txt | 通过；注册/重复/注入角色/CSRF/错误凭据/本人/冒用查询/运营/禁用/当前角色/到期/轮换/重用/并发/撤销/签名失败回滚/断库503 |
| 独立运行/迁移权限 | target/b02-provision.txt、target/b02-development-database.txt、target/database/*.txt | 开发与测试库通过；运行DML仅探针和4张身份表，DDL/历史/A/system/grant拒绝 |
| 运营受控入口 | target/b02-browser-operator.txt、target/b02-browser-operator-duplicate.txt | CLI成功、重复拒绝；浏览器验证当前OPERATOR权限 |
| Edge真实页面 | target/identity/browser.txt及两张PNG；target/b02-browser-run.txt | 注册/失败登录/登录/跨标签刷新与退出/运营按钮通过，页面错误0 |
| 正式前端构建 | target/b02-typescript6-install.txt、target/b02-frontend-ci.txt、target/b02-frontend-build.txt | TypeScript6.0.3精确版本/锁文件、npm ci、vue-tsc及Vite生产构建通过 |
| 正式一键验收/恢复 | target/b02-browser-final.txt、target/identity/environment-restore.txt | run-b02-browser.ps1通过，身份HTTP与浏览器通过，环境恢复通过；5173/18092临时端口已释放 |
| 普通B产物/启动 | target/identity/baseline.txt、target/b02-normal-start.txt | JDK21启动、根路由404、无Flyway/验收依赖、Java8拒绝；终端仍1.8.0_391 |
| RPC/MQ/签名基线 | target/environment-probe/b022-20261008 | PASSED：签名查询NOT_FOUND、非法签名AUTH_INVALID、SEND_OK、VERIFIED_APPLIED、PROCESSED_APPLIED、越权PERMISSION_DENIED |
| HTTP机器契约 | docs/b02-http-api.json（原目录） | 历史.2检查：16操作/279内部引用；当前13身份/商品操作已实现、3同步/试算操作待实现 |

2026-10-08收口：D9已由用户选择并落实TypeScript6.0.3；正式构建、一键浏览器验收和环境恢复通过，B-02.2标记已完成。没有未回答的.2方案选择；B-02整体仍需.3～.6完成，不自动开展后续阶段。尚未执行生产HTTPS部署、Docker B镜像启动或多实例/负载验收，未以这些为本轮成果。该项是.2收口时的历史范围：商品页及商品运营维护随后在.3核心实现，/admin/users/me只用于真实最小运营身份能力。

## 12. B-02.3 商品主数据与版本实施记录

2026-10-08：B-02.3已完成实际验收。用户确认D12沿用A的128个UTF-16单元上限，名称边界、完整回归及环境恢复通过。代码位于D:/Java/zj-market-b01，未提交或合并工作树；没有提前实现消息发送、结果消费、试算或交易业务。

### 12.1 实施拆分与完成条件

| 步骤 | 目标与依赖 | 验收标准与实际结果 |
| --- | --- | --- |
| ① 领域和持久事实 | 依赖.1/.2；建立Product、同步目标和完整快照事件，新增V3迁移 | BigDecimal、CNY、严格输入、精准标识、独立库/账号最小权限通过；D12长度边界通过 |
| ② 本地事务和HTTP | 依赖①；创建/完整编辑/上下架/分页/详情，锁定后比较expectedVersion | 6个操作、无权限拒绝、编码路径权限、并发只有一个成功、无变化无事件、展示字段编辑增版、事务故障整体回滚、A客户端禁用仍可提交通过 |
| ③ 商城和运营页面 | 依赖②；同一Vue工程接入列表/详情、创建/编辑/上下架 | Edge实际操作通过；匿名隐藏下架商品、图片失败占位、纯文本、409后不自动重发、显式重新读取、PENDING状态展示通过 |
| ④ 综合复验和交接 | 依赖①～③；构建、身份回归、数据库边界和环境恢复 | Maven15项、真实身份HTTP/浏览器及商品HTTP/浏览器通过；D12边界已补测并完成收口 |

### 12.2 最终实现与配置边界

- domain的Product是权威单SKU事实；goodsId为服务端UUID、ascii_bin精确匹配，直接作为A的goodsId。Fields使用BigDecimal原价、CNY和ON_SALE/OFF_SALE；HTTP输入必须为两位小数字符串，0.01～999999.99，不将JSON数字静默转成金额字符串。创建版本1、默认下架；缺省描述空串/图片null。名称按D10去首尾空白，描述原文保留，HTML标签拒绝；HTTPS图片必须有有效host且无userinfo/空白，B不抓取图片。
- application的ProductService与ProductStore/ProductEventPort保持纯Java依赖。ProductStore聚合商品仓储、事件保存、同步目标与显式本地事务端口；基础设施提供MyBatisProductStore和TransactionTemplate，同一DataSource、REPEATABLE_READ，使分页/详情的商品与进度一致。编辑先SELECT FOR UPDATE，再比较expectedVersion，并以WHERE product_version=expected条件更新；冲突409 PRODUCT_EDIT_CONFLICT。无变化返回原版本，溢出有效编辑409 PRODUCT_VERSION_EXHAUSTED。
- ContractProductEvents只在基础设施引用A契约和独立Jackson2 ContractCodec。提交时生成并保存完整9字段EventEnvelope和6字段ProductSnapshotChanged；eventId、版本、UTC毫秒occurredAt和关联requestId一起冻结。营销payload不含图片、描述或库存；历史body不从最新商品重建。图片/描述有效变化也增版并保存快照。
- 商品更新、b_product_outbox完整body、b_product_sync最新目标必须在一个本地事务提交。每次有效变化目标PENDING，保留历史confirmedVersion；syncReady仅在可信确认的版本等于当前目标及商品版本时为true。本阶段所有新事实仍待发布，没有将保存或SEND_OK当作A确认。B-02.4须在此基础上实现认领/租约/投递/结果/补查，禁止改写已保存body及事实时间。
- 三张新表b_product/b_product_outbox/b_product_sync由V3__product_authority.sql显式迁移；V1/V2未修改。开发zj_market与zj_market_b02_test均迁移至V3，运行账号各仅有探针、4张身份表和3张商品表DML。迁移历史/DDL/A/system/grant继续拒绝；迁移账号只在自己的B库执行DDL。普通app不含Flyway/验收程序，也不自动迁移。
- b.product.enabled默认false；商品HTTP需要显式开启身份与数据库。B_PRODUCT_EVENT_PRODUCER/SOURCE/CHANNEL外部注入，分别绑定producer/source/channel；可复用既有B_MQ_PRODUCER_ID（或AB_V2_RPC_CLIENT_ID）、B_MQ_SOURCE、B_MQ_CHANNEL，但不要求RPC/MQ客户端enabled。尚未提供正确事件归属时启动拒绝，不造默认渠道。身份和数据库维护CLI显式关闭商品模块，避免无关环境变量影响维护入口。
- 运营接口同时由访问过滤器和HTTP处理器当前Principal检查保护，含编码路径回归，不能仅凭原始URI判断角色。前端入口随当前角色显示；商品写请求只发送一次，过期时先刷新再发送，401/冲突/网络未知结果均不自动重发写操作；运营可显式重新读取，创建响应不确定时先核对管理列表。
- 前端沿用Vue3/TypeScript6.0.3/Vite，无新增产品依赖。/或/products进入公开列表，/products/{goodsId}支持详情直达；/admin/products为运营列表与编辑入口；保留/login、/register和身份页面。基础商品可浏览，未确认显示“资料更新中，暂不可试算”，不显示购买/支付流程。

### 12.3 复现命令

在PowerShell7、Docker已有mysql容器运行的环境，从工作树执行；所有Java入口复用b-runtime.ps1选实际JDK21，不改变终端/A的Java8。

```powershell
cd D:/Java/zj-market-b01
./docs/tests/run-b02-products.ps1
# 包已构建时的一键真实浏览器验收，包含身份HTTP/浏览器回归
./docs/tests/run-b02-products-browser.ps1 -SkipBuild
# 显式迁移开发库并验证最小权限（不创建业务样本）
./scripts/provision-b-database.ps1 -SkipBuild
```

一键验收只使用zj_market_b02_test与对应runtime/migrator账号，创建自有随机用户/商品样本，不清理A或开发业务数据；端口冲突拒绝运行，finally只停止本次启动的B/Vite进程。测试RSA私钥和DPAPI凭据仍在忽略.local目录中。

单独启动商品页面测试，需要外部身份配置及事件归属；以下沿用一键验收生成的学习测试密钥：

```powershell
$env:B_IDENTITY_ORIGIN='http://127.0.0.1:5173'
$env:B_IDENTITY_SECURE_COOKIES='false'
$env:B_IDENTITY_KEY_ID='b02-test'
$env:B_IDENTITY_PRIVATE_KEY_FILE='D:/Java/zj-market-b01/.local/b02-test-keys/private.pem'
$env:B_IDENTITY_PUBLIC_KEY_FILE='D:/Java/zj-market-b01/.local/b02-test-keys/public.pem'
$env:B_PRODUCT_EVENT_PRODUCER='zj-market'
$env:B_PRODUCT_EVENT_SOURCE='s01'
$env:B_PRODUCT_EVENT_CHANNEL='c01'
./scripts/start-products.ps1 -TestDatabase -SkipBuild
# 另一个终端：cd D:/Java/zj-market-b01/frontend; npm run dev
```

普通开发省略-TestDatabase，并使用自己的外部身份密钥/运行配置；部署仍要求HTTPS/Secure cookie，不直接复用学习测试私钥。start-identity.ps1继续是仅身份入口，start-products.ps1显式开启商品模块，二者复用同一个JDK21启动脚本。

### 12.4 证据与范围

| 验收 | 工作树忽略目录证据 | 结果 |
| --- | --- | --- |
| 模块/边界/签名/RSA/普通引导 | target/b023-d12-http.txt中Maven结果，各模块surefire-reports | 15项通过；最终商品CLI在Java21.0.2/Boot4.1.1运行 |
| 商品6个真实HTTP操作及MySQL | target/products/verify.txt | 权限、编码路径、价格/类型/币种/版本、精准ID、默认值、并发、无变化、展示编辑增版、完整历史body、事务故障回滚、断库503通过 |
| 开发库V3/权限 | target/products/development-migrate.txt、development-permissions.txt；target/b023-development-database.txt | V3显式执行及最小授权通过 |
| 测试库V3/权限 | target/database/migrate.txt、verify.txt；target/b023-products-final.txt | 重复迁移0条、最小授权通过 |
| 商品及身份真实Edge页面 | target/products/browser.txt、store.png、operator.png；target/identity/browser.txt、verify.txt | 主要商品操作和身份回归通过，页面错误0 |
| 前端正式类型/生产构建 | target/b02-frontend-ci.txt、target/b02-frontend-build.txt | TypeScript6.0.3锁文件及构建通过 |
| 普通包/环境恢复 | target/products/environment-restore.txt；target/b023-browser-final.txt | 调用方全部环境恢复、18092/5173释放、终端Java8保持、普通包无Flyway/验收程序通过 |
| A离线边界 | ProductCommands显式关闭RPC/MQ后的真实HTTP提交 | 商品/完整事件本地提交通过；未发送MQ或宣称A已应用 |

D12已由用户确认：B沿用A的128个UTF-16单元上限，emoji通常占2个。后端名称strip/trim后用String.length；前端使用JS字符串长度提示和校验，后端实施最终校验。实测128个普通中文、64个emoji、126个ASCII加1个emoji的创建/编辑成功；129个ASCII、65个emoji、127个ASCII加1个emoji的创建/编辑拒绝400，原商品版本和事件数不变；数据库及冻结A快照完整保留合法名称。浏览器显示上限说明，65个emoji在发送写请求前被拒绝。

机器契约goodsName保留标准maxLength=128（Unicode字符的必要上界），通过x-max-utf16-units=128和description明确额外UTF-16限制，不能仅用标准maxLength代替服务器校验。D12复验证据为target/b023-d12-http.txt、target/b023-d12-browser.txt、target/products/verify.txt、browser.txt和d12-environment-restore.txt；15项Maven测试、真实身份/商品HTTP及浏览器、正式类型/生产构建均通过，全部调用方环境恢复、临时18092/5173释放、终端Java8保持。**B-02.3标记已完成，没有未回答的.3方案选择。**

此前B-02.2的RPC/MQ/签名实测target/environment-probe/b022-20261008继续作为已验证基线；本轮未改依赖版本/签名编解码，也未重复发送消息。可靠投递和A持久确认、试算、生产HTTPS/Docker及负载仍归后续范围。

## 13. B-02.4可靠同步实施记录

2026-10-08开始。用户确认后的D13～D16覆盖最初待修正的提问：生产发送失败退避1/2/4/8分钟，5次告警后持续按8分钟上限重试，运营可暂停/恢复；学习验收只在独立B测试库使用2～8秒加速。扫描2秒、认领租约30秒、每轮20条、结果补查30秒。毒消息先持久隔离后确认，隔离失败按技术故障重试；运营页面只脱敏查询，重放由受控维护入口重新验签。业务结果消费最多重新消费8次，独立组实测死信，不调整A业务组策略。

| 步骤 | 目标及依赖 | 验收 |
| --- | --- | --- |
| ① 持久认领与发布 | 依赖.3；显式V4迁移、行锁后数据库计时、租约token防旧持有者更新、原始正文签名发布 | 发送失败保留事实；租约过期/进程重启可恢复；SEND_OK仅记录Broker确认 |
| ② 结果验签与原子提交 | 依赖①；Topic/Tag/producer/keyId/渠道/严格结构校验，Inbox摘要和结果与进度同事务 | 重复无副作用、同ID异正文隔离、技术失败不确认、旧结果不回退当前目标 |
| ③ 补查与受控恢复 | 依赖②；queryEventResult、脱敏异常查询、暂停/恢复、受控原事件重投及隔离维护 | NOT_FOUND/WAITING不视为成功；发布后缺结果先查询；确定拒绝/矛盾证据不无限重投 |
| ④ 隔离联合验收 | 依赖①～③；真实B/MySQL/RPC/MQ、身份商品回归、浏览器与重启/死信 | 通过实际故障矩阵后标记.4完成，保留命令、证据和环境恢复记录 |

当前已实现SDK-free应用端口/服务、V4迁移、持久租约/Inbox/隔离/审计、严格结果解码、懒启动MQ/RPC适配，以及运营HTTP/页面。开发及隔离测试库V4和11表最小授权通过；真实A/B、死信、受控维护、最终边界及页面联调均通过，四步验收完成，B-02.4标记已完成。可靠同步不改变商品权威主数据，不提前实现优惠试算或交易业务。

### 13.1 实际实现及配置边界

- 继续复用.3商品、冻结事件及目标同事务保存。Outbox新增正文摘要、原快照售卖状态、发送/补查次数、失败次数、下次时间、认领token/租约和结果证据；新增b_sync_inbox、b_sync_quarantine、b_sync_audit，不设计订单/库存/支付表。
- 认领使用FOR UPDATE SKIP LOCKED，锁定后读取数据库时间；发送与RPC在短事务之外执行，落库校验token及租约。旧持有者不能记录新租约的确认。发送窗口不确定时仍使用原eventId、冻结body和occurredAt，重新计算当前可信keyId的消息签名。
- SEND_OK只表示Broker确认，商品syncReady仍为false。仅可信APPLIED或同版本IGNORED、关联原事件/商品/版本/售卖状态一致时才确认；较大/较小版本或矛盾证据进入核对。同版本业务拒绝停止原事实重投，新编辑创建新版本。旧回执只记录历史证据/确认版本，不覆盖新目标；结果矛盾的核对状态不会被后续原结果重复抹除。
- MQ按实际Topic和原字节验签，校验Tag、producer、可信keyId、source/channel、严格字段和UTC毫秒时间、结果语义，拒绝重复JSON键。Inbox按业务消费者/producer/回执ID唯一，摘要相同幂等，异正文隔离。结果、Inbox与目标进度同事务；数据库异常不确认消费。隔离只保存最多256KiB原字节，超限保存摘要与大小且不能维护重放。
- queryEventResult沿用Triple TLS、独立签名编解码及新nonce/timestamp/requestId。NOT_FOUND/WAITING_DEPENDENCY继续待处理，不自动盲目重发已发布事件；运营恢复先做可信补查，仅NOT_FOUND允许原事件重新排队。已确认/拒绝/矛盾/过期目标本地拒绝409，A离线也不能绕过。
- 单实例后台任务每2秒扫描、最多20次认领、租约30秒、结果补查30秒；生产发送退避1/2/4/8分钟后8分钟封顶，连续第5次输出脱敏告警并持久保留PUBLISH_FAILED_ALERT，继续恢复。运营暂停/恢复有审计。学习秒级退避只能在精确隔离测试库及账号开启。
- 正式同步消费者使用独立B_PRODUCT_SYNC_RESULTS-dev，业务最大重新消费次数固定8，禁止旧兼容探针组及独立死信测试组作为业务入口。独立测试组B_SYNC_RETRY_TEST-dev使用1次重试与Broker第1延迟级别实测死信，B_SYNC_DLQ_READER-dev读取自有死信；不改A业务策略，不停止共享Broker/MySQL。

### 13.2 启动和受控维护

普通启动默认不启用同步。start-identity.ps1只启用身份；start-products.ps1启用商品；完整商品同步通过start-sync.ps1显式启用身份/商品/RPC/MQ/后台任务，全部复用原JDK21入口。V4须由显式迁移入口先完成，普通包没有Flyway或验收程序，也不继承迁移账号及仅用于消息验收的A Broker账号。

启动前外部注入已有身份RS256配置、B运行数据库凭据、B RPC签名/TLS配置和B MQ账号/签名配置。B_PRODUCT_EVENT_PRODUCER/SOURCE/CHANNEL须与RPC/MQ身份和渠道一致。正式MQ默认TLS；本轮沿用B-01明确许可的127.0.0.1学习Broker明文连接和ACL，不能据此声称生产MQ TLS或跨主机验收完成。

```powershell
cd D:/Java/zj-market-b01
# 运行凭据来自忽略.local文件或外部环境，不把真实密钥放进命令/文档。
./scripts/start-sync.ps1 -SkipBuild
# 学习测试库使用 -TestDatabase；不能将秒级加速用于开发/生产库。
```

关键外部项：B_MQ_RESULT_GROUP独立业务组，B_RPC_URL/GROUP及CLIENT_CERT/CLIENT_KEY/TRUST_CERT，B_MQ_NAMESERVER及ACCESS_KEY/SECRET_KEY，B_MQ_B_KEY_ID/B_MQ_B_SECRET、B_MQ_A_KEY_ID/B_MQ_A_SECRET、三个Topic及source/channel。以前A结果签名keyId和secret通过B_SYNC_PREVIOUS_A_KEYS按kid=secret分号分隔外部注入；保留覆盖历史消息的可信旧键，不能跳过验签。B_SYNC_ENABLED默认false，其他参数B_SYNC_SCAN_MILLIS=2000、B_SYNC_LEASE_MILLIS=30000、B_SYNC_QUERY_MILLIS=30000、B_SYNC_BATCH_SIZE=20、B_SYNC_MAX_RECONSUME_TIMES=8；B_SYNC_ACCELERATED_TEST默认false。

运营页面可读取最新同步状态、暂停自动同步、核对并恢复原事件，202只表示排队；冲突/拒绝提示重新读取核对，不自动重放请求。隔离页面只查询quarantineId、bodyHash、reason、originalSize、storedAt、state，支持分页；无正文、签名、密钥和浏览器重放入口。修复可信配置后，受控维护入口仍按原字节重新验签/校验并持久提交，失败保持隔离；target/sync/maintenance-cli.txt记录真实独立CLI重验及重复回执幂等通过：

```powershell
# 先外部注入与正式同步一致的可信签名/TLS/身份/运行配置。
./scripts/sync.ps1 -QuarantineId '<待核对记录ID>' -SkipBuild
# 明确使用学习库时增加 -TestDatabase；此入口不会替换消息正文。
```

### 13.3 复现和证据

完整复现依赖B-01已有本地MySQL/Redis/RocketMQ、A构建包及既有隔离A测试库、忽略.local外部凭据，复用B-02身份学习密钥。脚本显式JDK21运行B、JDK8运行自有A提供方，分别连接zj_market_b02_test和group_buy_market_phase1_test，随机自有业务样本，不清洗开发库/A业务数据。

```powershell
cd D:/Java/zj-market-b01
./scripts/mvn.ps1 -MavenArguments @('-B','package')
./docs/tests/run-b02-sync.ps1 -SkipBuild -Browser
# 仅联调故障矩阵：省略 -Browser；每次创建新的target/sync运行目录。
```

脚本先在A离线下保存/发布事实后退出B，再启动自有隔离A及第二个B验收进程，复验持久恢复；使用正确RPC组gbm-dev、临时自签测试TLS及独立结果消费组。本地ACL仅扩展B独立组和带引号的自有死信Topic订阅，Broker热更新，不重启共享服务。A Broker发布凭据仅用于显式verification进程的真实结果测试，普通B启动清除此类变量；脚本finally停止自有进程、恢复调用方全部环境。

| 验收层次 | 已验证范围 | 证据（工作树忽略target） |
| --- | --- | --- |
| 真实JDK21/Boot/模块 | 原版本组合；15项边界/编解码/RSA/普通引导测试；六模块打包 | b024-package.txt及surefire-reports |
| 真实MySQL及受控故障输入 | 原子Inbox/结果/进度；写后注入异常回滚；重复/异正文/严格结构/错签/旧可信键重放；token排他和过期防旧ACK；六次发送失败仍恢复；WAITING不确认 | 各次target/sync/b024-*/verify.txt；部分异常用明确的应用端口故障及自有fixture时间输入，不称为停止实际共享数据库 |
| 实际A/B RPC/MQ | A离线提交、Broker确认不等于A应用；B进程重启及发送后未落库窗口恢复；签名结果消费；丢结果RPC补查；NOT_FOUND受控原事件重投 | 运行目录prepare.txt、verify.txt及忽略A/B日志 |
| 实际A版本语义 | 同版本异内容REJECTED且B主数据不变；新版本修正；v3先于v1/v2，较大版本IGNORED不回退最新确认 | verify.txt的actual-A版本矩阵 |
| 实际Broker死信及恢复 | 独立组初次＋1次重试后死信，原字节不变；故障源为注入数据库访问异常的正式结果读取端口；业务仍8次配置；待确认事实通过真实queryEventResult恢复 | verify.txt的isolated-maxRetry1及pending-before-DLQ/RPC-recovery；未声称业务组进行了9次消费 |
| 实际HTTP/权限 | OPERATOR状态/暂停/原事件恢复、版本/参数严格校验、USER403/匿名401、编码路径、六项脱敏隔离查询 | verify.txt的actual-HTTP矩阵 |
| 实际Edge/后台 | 页面暂停/恢复、自有正常B后台自动发布与A/MQ确认、确认当前版本、隔离只读、商城确认展示；身份/商品回归、无页面异常 | target/sync/browser.txt、operator.png、store.png；target/identity/browser.txt、target/products/browser.txt |
| 数据库与环境 | 开发/测试V4及11表最小DML，DDL/history/A/system/grant拒绝；环境恢复、临时端口释放、终端默认Java8、普通包边界 | b024-development-database.txt、development-verify.txt、target/sync/*database-permissions.txt、environment-restore.txt、default-java.txt |

最终实现证据：核心故障矩阵为target/sync/b024-20261008-195839/verify.txt与target/b024-final-core.txt；最终Maven15项/打包为target/b024-package.txt；页面版本一致性修正后复验为target/b024-final-browser.txt与target/sync/browser.txt，每次单独生成新的暂停样本并定位详情区域，隔离页面测试扫描5秒，正式默认仍2秒。身份/商品原回归为target/b024-final-run.txt；最后控制脚本及启动边界不改变商品核心，按受影响入口复验，没有把历史截图或模拟输入替代实际联调。

机器契约新增暂停和只读隔离查询，当前18个HTTP操作中17个实现，优惠试算仍计划中；全部本地引用有效。B-02.4不宣称生产跨主机/TLS、负载、多个B实例、告警平台或业务组9次实际消费验收完成，相关部署/扩容验收归后续阶段。

## 14. B-02.5 A试算与商城浏览实施记录

2026-10-08开始。继续使用原工作树和固定JDK21/Boot4.1.1/Netty/独立签名编解码，不新增订单、库存、支付或试算缓存表。用户已选择D17：登录后进入商品详情自动试算，提供“重新试算”；无登录不向A伪造匿名用户，商品版本或身份变化清除旧试算。 D18选择每3秒读取B商品资料、最多1分钟；到期停止自动读取并提供手动刷新，未确认同步前不调用A，确认后恢复自动试算。

| 步骤 | 目标及依赖 | 验收 |
| --- | --- | --- |
| ① 当前事实与HTTP边界 | 依赖.2～.4；从实际认证取得userId，B当前在售且同步确认版本，空正文POST | 伪造身份/价格/版本/活动/数量拒绝；未同步不调用A；RPC外没有本地事务 |
| ② A适配与输出校验 | 依赖①；MarketingService.trial真实TLS及独立签名，新nonce/时间/请求ID；回读本地版本 | 无公开优惠/不可见不泄露；公开不具资格单独展示；金额/布尔/时间/归属严格校验；异常不是无活动；在途改版丢弃旧结果 |
| ③ 商城页面接入 | 依赖①②及D17；首页/列表/详情、登录返回站内商品、自动试算/重新试算 | 无跨用户/版本陈旧优惠；展示真实A结果；无虚假购买/支付流程 |
| ④ 隔离联合验收 | 依赖①～③；自有A/B测试数据与正常B网页，故障/权限/版本/页面回归 | 真实RPC/MQ/HTTP/浏览器证据、构建及环境恢复齐备后标记完成 |

应用端口/服务、Dubbo试算适配、受保护HTTP与start-market.ps1完整商城启动入口已完成实际验收，第14节四步均通过，B-02.5已完成。真实A活动样本只写已有A隔离测试库的自有随机ID，不清理开发业务数据。

### 14.1 实际实现及配置边界

POST /api/v1/products/{goodsId}/trial仅接受空JSON对象，不接受查询参数。登录身份只来自B认证上下文，USER和OPERATOR均可调用；商品须为B当前在售且同步确认版本。前后两次本地读取各用短事务，中间RPC不占用数据库事务；返回后版本、目标事件或售卖状态变化则拒绝旧结果。

请求只由B填入当前userId、goodsId、productVersion、source/channel及quantity=1，activityId为空交A选择。复用固定Triple TLS、独立Jackson2签名编解码，每次重新生成nonce、时间和请求ID，无自动RPC重试。A签名错误映射502 INTEGRATION_AUTH_FAILED，不映射浏览器401；连接异常503、超时504、无效响应502、同步中及改版409。

成功输出只含goodsId、productVersion、quotedAt、state、offer。不可见或无活动统一NO_PUBLIC_OFFER、offer=null，不泄露活动编号、价格和A内部reasonCode。公开但不具资格用INELIGIBLE，明确展示活动参考价；具资格且合法完整offer用AVAILABLE。布尔值、UTC毫秒时间、商品及版本归属、CNY、两位小数金额、原价等于B当前原价、原价减优惠等于估算价、人数1～100均校验。

首页与/products共用商品列表，详情匿名可浏览。登录返回仅允许站内商城路径；D17自动试算及手动重试，结果不缓存，身份/版本变化或页面离开后丢弃迟到结果。展示报价前再读B当前资料，发现改版丢弃旧报价。D18同步未确认时每3秒读取B，最多1分钟后停止，可手动刷新；同一版本的普通刷新不会重复试算或重置计时。试算不是价格或资格保留，后续交易须重新验证；当前没有下单/支付入口。

完整入口scripts/start-market.ps1开启身份、商品、同步、RPC/MQ及试算；原身份/商品/同步单独入口显式关闭试算。普通包不执行迁移且不包含verification/Flyway；凭据仍外部注入，普通启动额外清除本轮验收账号变量。数据库仍为V4与11表，不新增试算或交易表。
### 14.2 复现入口及实际证据边界

```powershell
cd D:/Java/zj-market-b01
./scripts/mvn.ps1 -MavenArguments @('-B','package')
./docs/tests/run-b02-trial.ps1 -SkipBuild -Browser
# 仅核心HTTP/RPC/MQ/签名/版本与离线验收：省略-Browser。
# 普通完整商城：先外部注入既有配置，再运行以下入口。
./scripts/start-market.ps1 -SkipBuild
```

联合脚本显式JDK21运行B、JDK8运行自有A，限定zj_market_b02_test及group_buy_market_phase1_test。A优先使用外部PHASE1_DB_PASSWORD/SPRING_DATASOURCE_PASSWORD，本地隔离验收可复用既有学习MySQL容器凭据；不把配置占位符当密码，不输出凭据，不传给B。A启动快照剔除B变量，启动后完整恢复B环境。随机普通用户/标签成员/运营账号密码仅在验收进程环境中存续，manifest只保存自有样本ID；正常B启动清除验收账号变量。

活动仅INSERT自有随机数值折扣ID、活动ID、渠道映射及标签主记录/成员明细；无活动样本不建映射。脚本先核对已有A商品/用户ID字段容量64，不自动升级A结构、不清理A数据。商品同步使用.4真实MQ和独立消费者，再调用真实A TLS试算。页面使用正常zj-market-app-exec.jar而非verification上下文，无假优惠替代真实A。

核心已通过真实A的公开价格、不具资格、隐藏/无活动脱敏、本人精确标签资格、错误RPC签名，以及真实运营HTTP在RPC结果返回窗口内修改商品。受控坏报价和坏RPC信封通过正式应用/解码入口；实际SDK超时通过独立TLS连接接收流量后不响应验证，明确不是停止真实A造成超时。真正A不可用通过停止本轮自有A进程验证，保持共享MySQL/Redis/Broker运行。

正常浏览器覆盖匿名资料、登录安全返回、自动试算及单次手动重算、不同身份结果和退出、真实有效报价在传输中延迟且运营改版后丢弃、同步暂停的一分钟读取上限和到期手动刷新。上述实际页面验收及A离线页面均通过；15项Maven测试/打包、真实可靠同步故障矩阵、原身份/商品HTTP及浏览器回归通过。全部调用方环境恢复，默认Java8及自有端口释放已确认。
### 14.3 最终验收与收口（2026-10-08）

| 层次 | 实际已通过 | 证据（zj-market-b01忽略target） |
| --- | --- | --- |
| 固定环境及正常包 | JDK21.0.2、Boot4.1.1、Netty固定/原签名；15项Maven测试及六模块打包；正常包没有verification/Flyway | b025-package.txt、trial/normal-package-boundary.txt |
| 真实A/B | 五个商品真实MQ确认后试算；公开100.00减10.00得90.00、公开不具资格、隐藏/无活动无泄露、本人精确标签资格；新签名/nonce/TLS | trial/b025-20261008-214435/verify.txt，最终核心trial/b025-20261008-214819/verify.txt、b025-final-core.txt |
| HTTP/竞态及异常 | 空正文/无查询参数、真实认证和编码路径、未同步/下架不调用A、no-store；真实运营在A结果返回窗口改版后409拒绝旧报价，确认新版本后试算；真实错误签名502 | 同上verify.txt；RPC期间无数据库事务 |
| 明确受控故障 | 坏报价/信封用正式校验入口：布尔/时间/归属/金额/人数/null/requestId；独立TLS停滞接收实际SDK流量后超时504 | verify.txt明确标注controlled输入及actual-SDK-stalled-TLS；不称其为真实A返回坏报价 |
| 正常Edge页面 | 匿名首页/列表/详情、登录安全返回、自动试算和单次手动重算、不同身份/退出；真实报价在传输中延迟并发改版后丢弃；实际60秒只读B、停止自动刷新、确认后手动刷新恢复试算；无页面异常 | trial/b025-20261008-214435/browser.txt、live-browser-run.txt；trial/browser.txt、store.png |
| 实际A离线 | 停止本轮自有A进程后，正常B仍启动/浏览；自动与手动试算显示服务异常，不称无优惠或登录失效 | 同一运行目录browser-offline.txt、offline-browser-run.txt、offline.txt；最终核心offline.txt |
| 原功能回归 | 真实可靠同步签名/补查/版本/死信；原身份和商品HTTP/权限/边界及Edge运营编辑回归 | sync/b024-20261008-214923/verify.txt、b025-sync-regression.txt、b025-browser-regression.txt、identity/browser.txt、products/browser.txt |
| 机器契约及环境 | 18个HTTP操作全部实现，316个本地引用有效；测试库V4与11表权限仍通过；全部环境变量恢复、自有18091/50051/18092/5173释放、终端Java8保持 | trial/http-contract.txt、trial/environment-restore.txt、trial/default-java.txt、database/verify.txt |

本轮不新增数据库迁移或试算缓存表，保留V4与11表最小运行权限；正常B与验收入口及外部凭据边界保持。为复用A现有外部密码配置，同时修正旧可靠同步验收脚本的凭据读取和临时A环境恢复；真实同步回归通过。未提交/合并、修改A源码、清洗A数据或提前开展B-02.6。B-02.5收口时整体等待.6综合验收；当前整体联合验收完成状态见第15节，生产部署/跨主机TLS/负载不据此标记完成。

## 15. B-02.6 联合验收与交接实施记录

2026-10-08开始。承接原工作树与D1～D18全部用户选择，不新增交易业务表、不修改A源码、不提交或合并。联合验收入口docs/tests/run-b02-acceptance.ps1，证据独立存放target/acceptance的新运行目录，完整结果通过后才能将B-02整体标记完成。

| 步骤 | 依赖及目标 | 验收条件 |
| --- | --- | --- |
| ① 固定构建与边界 | 依赖.1～.5；JDK21构建、依赖树、正常包、开发/测试库V4校验及权限 | 原版本与15项测试通过；无新迁移；11表运行DML、DDL/history/A/system/grant及跨B库拒绝 |
| ② 实际闭环与恢复 | 依赖①；身份/商品HTTP与页面、真实A/MQ/RPC、同步故障、试算与离线页面 | 既有矩阵全通过；补验真实结果提交后、Broker ACK前硬退出，另一B进程重复消费且Inbox仍一条 |
| ③ 证据、前置与交接 | 依赖①②；汇总证据及产物指纹、HTTP清单、B-01前置收尾、B-03字段与遗留项 | 所有报告有明确通过状态，环境/端口恢复；交接标识与价格语义明确；不将试算当价格保留或创建交易业务 |

当前统一入口实际验收已通过，B-02.6完成；状态以本轮联合报告及补充只读元数据审计为依据。新增故障触发仅打包进verification，普通app不包含；业务组仍最多重新消费8次，不重启共享MySQL/Redis/Broker。
### 15.1 统一复现与报告

```powershell
cd D:/Java/zj-market-b01
./docs/tests/run-b02-acceptance.ps1
# 已完成本轮JDK21构建时，可使用-SkipBuild；仍校验运行及依赖边界。
```

入口复用已有显式JDK选择和阶段脚本，顺序执行构建/依赖树、双B库迁移及权限、真实同步/硬退出恢复和身份商品/运营页面、真实试算及在线/离线商城、原中间件签名与ACL基线。证据在target/acceptance/<RunName>/report.json，包含步骤、独立报告位置、普通app与verification包及前端锁文件SHA256、环境恢复和自有端口释放结果。每次新建目录，不覆盖旧运行证据；日志与本地凭据在忽略目录中，报告不含密码、令牌或签名密钥。

### 15.2 B-01前置收尾交接

| 前置项 | B-02已落实及本次核对 | 边界 |
| --- | --- | --- |
| 实际运行基线 | B脚本显式JDK21，Boot4.1.1/Netty及独立Jackson签名组合；普通包/独立验收包分离 | A与终端仍JDK8，不修改系统JAVA_HOME/PATH |
| 开发与验收隔离 | zj_market/zj_market_app与zj_market_b02_test/zj_market_b02_test_app；独立迁移账号；精准scope防误用 | 两个B库互相拒绝访问，B账号不能访问A库；真实测试只创建自己的隔离业务样本 |
| 请求与事件关联约定 | HTTP生成requestId并一致返回X-Request-Id/响应；商品写入将其保存为快照correlationId；结果通过originalEventId关联原事件；试算RPC沿用HTTP请求ID并核对回传；补查使用新请求ID与原eventId | eventId是幂等事实标识，requestId是一次调用标识；重投不生成新事实。已有真实HTTP/RPC/消息校验覆盖；没有宣称已建设集中追踪或监控平台 |
| 本机技术验收与遗留归属 | 重跑原RPC/MQ/签名及越权发布基线，与现有正式业务消费组区分 | 本机自签Triple、MQ回环明文例外、外部凭据的实际验收；正式证书/跨主机/生产数据库TLS、Docker及IDE实机验收、备份与负载归部署阶段，不作为B-02交易能力 |

本节交接B-02所需前置项，不补建B-01过程文档，不把未验收的生产部署能力标记完成，也不替换A的开发路线与状态。

### 15.3 B-03输入字段与语义交接

以下是已实现B字段及A响应的映射，不是提前设计订单/库存/支付表或新HTTP接口。

| 输入 | 已有来源/形式 | B-03必须保持的语义 |
| --- | --- | --- |
| userId | B当前认证上下文；稳定不透明字符串，至多64字符，精确比较 | 从认证取得，不用loginName代替，不接受浏览器冒用；请求仍核验当前用户、登录撤销及权限 |
| goodsId/SKU | B商品goodsId；首版goodsId就是单SKU标识，至多64字符 | 作为后续商品/库存/订单关联键，不新增重复A/B映射，不能用商品名称作键 |
| productVersion | B统一正整数版本，以十进制字符串跨HTTP/RPC/MQ传递 | 不转JS Number；新购买重新读取当前版本、在售状态及确认进度；图片/描述等有效编辑也升版 |
| originalPrice/currency | B当前商品基础价；精确十进制/两位小数字符串、CNY，0.01～999999.99 | 不信任浏览器价格；订单应保存业务确认时的价格快照，不能以后用商品现价改写历史金额 |
| quantity | 当前试算由B固定1，首版单SKU范围 | 后续数量或多SKU方案若扩展须再交用户选择，不能把现在试算当任意数量报价 |
| activityId | A公开offer的正整数活动标识，以字符串传递；由A选择活动 | 不信任浏览器指定活动，不泄露不可见活动；后续以A真实占位/参团契约重新核验 |
| deductionPrice/payPrice | A合法公开offer；两位小数字符串，原价减优惠等于实付，实付至少0.01 | 当前仅试算参考；B-03必须重新确认并冻结交易价格，不将旧页面结果直接作为可信支付金额 |
| quotedAt/state/offer | UTC毫秒时间；AVAILABLE/INELIGIBLE/NO_PUBLIC_OFFER，隐藏或无活动offer=null | AVAILABLE只代表当次试算，未保留资格、库存或价格；无公开优惠不代表可跳过后续购买规则；故障不能伪装成无活动 |
| targetCount | A公开offer中的1～100人数 | 是营销成团参数，不是B可扣减库存或剩余库存 |
| eventId/targetEventId/confirmedVersion | B不可变事件及当前同步进度；RPC/MQ确认A营销副本 | Broker确认不是A应用；旧回执不能确认新版本，不把这些标识当订单号或支付流水 |

B-03接续条件：继续在已验收工作树开发，固定依赖与D1～D18；实际开始时另建唯一docs/b03-development.md。库存模型与预留释放、订单幂等/状态机、A占位衔接、失败补偿及支付退款价格快照等具体方案，在B-03范围设计时交用户确认。本阶段不提前选定或实现，不自动开始B-03，也不提交/合并当前未提交改动。
### 15.4 本轮矩阵、剩余项及完成状态

实际运行批次b026-20261008-220506，总报告[target/acceptance/b026-20261008-220506/report.json](D:/Java/zj-market-b01/target/acceptance/b026-20261008-220506/report.json)为PASSED。以下均是本轮产物及运行结果，不借用旧阶段通过状态：

| 验收项 | 本轮实际结果 | 报告 |
| --- | --- | --- |
| JDK/构建/模块 | JDK21.0.2、Boot4.1.1及原固定组合；15项测试无失败，六模块及独立验收包打包，正常包无verification/Flyway | acceptance/b026-20261008-220506/build.log、dependencies.log、package-boundary.txt；各模块target/b026-dependencies.txt |
| 双B库迁移/权限 | 开发/验收库Flyway校验成功，migrationsExecuted=0；运行与迁移权限及跨B/A/系统/DDL/history/grant负向检查通过；只读元数据补查各11表、成功V1～V4 | 同目录development-migrate/verify.txt、b02-test-migrate/verify.txt、schema-audit.txt |
| 身份与商品 | 注册/登录失败、过期、撤销、轮换重用、限流、USER/OPERATOR；商品金额/名称边界、上下架、并发版本、原子回滚；实际HTTP及Edge | synchronization.log；identity/products-browser.txt、target/identity/verify.txt及target/products/verify.txt |
| 可靠同步及故障 | A离线可提交、SEND_OK不等于应用、重启恢复、原事件重投、签名/隔离/重复/乱序/冲突/结果丢失及RPC补查；独立组真实死信后恢复，业务仍最多8次重新消费 | sync/b026-20261008-220506-sync/prepare.txt、verify.txt |
| 消费提交/ACK窗口 | 实际A签名回执经正式reader提交MySQL，验收进程halt(86)在ACK前硬退出；新进程收到同回执且正文摘要一致，Inbox仍一条、当前版本确认保持 | 同目录ack-committed.json、ack-recovery.txt及两进程日志；生产包无故障开关 |
| 真实A试算与商城 | 公开活动/无活动/不可见/不具资格/成员身份；当前身份及版本、并发改版、真实TLS、异常与超时；正常Edge自动/手动试算、安全返回、实际一分钟刷新上限及A进程停止后的页面 | trial/b026-20261008-220506-trial/verify.txt、browser.txt、browser-offline.txt、offline.txt |
| 原中间件基线 | 合法RPC查询NOT_FOUND，错签AUTH_INVALID；真实MQ SEND_OK、VERIFIED_APPLIED、持久PROCESSED_APPLIED、订阅AUTHORIZED及越权发布PERMISSION_DENIED | environment-probe/b026-20261008-220506-baseline/report.json |
| 契约、环境与产物 | HTTP18操作全部实现、316本地引用有效；调用方全部环境恢复，变更数0；50051/18091/18092/5173释放，默认Java8；JAR/前端锁文件SHA256记录 | acceptance/b026-20261008-220506/http-contract.txt、default-java.txt、report.json |

同轮身份/商品/sync页面报告已复制到联合目录，防止其他运行改写通用报告时混用。试算及同步核心使用带本轮RunName的独立目录。SDK超时和无效报价明确作为受控故障输入，与真实A的成功和离线分开记录；数据库故障端口、测试租约时间及独立死信组仍沿用.4实际范围，不虚称停掉共享数据库/Broker或实测业务组9次消费。

B-01本地工程/环境前置已按第15.2节交接。B-02.1～.6全部完成，闭环范围仅身份、商品、可靠同步、试算与浏览。B-03库存/订单/A占位、B-04支付/退款、后续履约及生产部署/正式TLS/跨主机/备份/监控/性能验收按路线图后续阶段推进；尚未确定的模型、幂等、补偿及压测目标届时交用户选择，不虚构QPS或提前建表。现有单实例限流与本机学习TLS/凭据例外不扩展为多实例或生产能力。

本轮未升级/降级框架、修改A源码、重置/清洗业务数据、提交/合并工作树或开展B-03；已有未提交修改保持。普通入口仍start-market.ps1，迁移仍显式database.ps1。此次联合验收与交接复杂度中等，按第15节三步完成；B-02整体实现复杂度高。

### 15.5 上传远程仓库前的敏感内容检查（2026-10-08）

原目录与实际开发工作树的 `.gitignore` 已统一补齐：本地 `.local/`、环境文件、私钥/密钥容器、凭据文件、日志/HAR/堆转储、数据库压缩备份、各模块构建输出及前端依赖/产物均排除。环境模板可以提交，但必须使用占位符；迁移 SQL、前端 `package-lock.json` 和可移植 `.run/B_JDK21.run.xml` 保留。

本轮检查覆盖两处工作目录的已跟踪及未忽略文件、暂存区和全部可达 Git 历史（1 个提交），并比对本机实际使用的 4 项 B 数据库密码及识别出的 7 项外部中间件秘密。扫描未发现这些真实凭据、完整私钥或真实令牌出现在待提交内容或已检查历史中；疑似项核对为外部注入、交互读取、运行时生成代码、接口字段或受控测试输入。忽略边界检查通过，已跟踪但应忽略的文件数为 0；本地凭据与验收证据保留在磁盘并排除上传。扫描结果限于本次检查范围，不作为任意未来文件的安全保证。

完整业务代码仍位于 `D:/Java/zj-market-b01` 的 `codex/b-01` 工作树，唯一 B-02 开发过程文档与 HTTP 契约位于原目录 `D:/Java/zj-market/docs`；原目录 `master` 仍是初始工程。实际提交/上传时须明确整理代码与文档所在分支，不能把仅上传原目录视为已上传 B-02。本轮未提交、合并、改写历史或推送，也未删除本地凭据、改动业务代码或重复执行业务联合验收。此次检查与忽略规则清理复杂度低。

### 15.6 B-02本地提交与主分支合并（2026-10-08）

用户授权本地提交与合并，并提供提交作者ZJ及邮箱；作者设置只写入B仓库配置，不影响A或全局Git配置。`b-02` 已提交为 `9d75f82`，共142个变更文件，包含身份/商品/可靠同步/商城、前端、启动与验收脚本、DDD模块和安全忽略规则。提交前检查确认敏感文件、生成产物及已跟踪但应忽略文件均为0；两个验收脚本只修正行尾格式并通过语法检查，没有重跑或冒称新增业务验收。

原目录的 `master` 尚无首次提交，已将 `b-02` 快进合并到 `master`，随后补入原目录唯一B-02过程文档、HTTP契约、最新路线图及交接记录。主目录 `D:/Java/zj-market` 现为完整工程；开发工作树 `D:/Java/zj-market-b01` 保留在 `b-02`。原目录14个文件和原始索引在操作前已保留于忽略目录 `target/merge-b02-20261008-224649`，逐文件SHA256核对通过，旧初始化源码没有覆盖已实现的模块工程。

以上更新覆盖历史记录中“原目录仍是初始工程”“尚未提交/合并”的当前状态，历史验收范围与证据保持。本次不推送远程、不合并远程分支、不改写历史、不删除本地凭据、不开展B-03。此次本地归档复杂度中等：保全原目录改动 → 提交b-02 → 快进主分支 → 补齐权威文档及状态验证。

## 16. 此次任务实施复杂度

B-02.4为高，难点是跨进程发送窗口、数据库租约、结果去重/乱序、签名校验、查询补偿、毒消息隔离及死信恢复。第13节四步均已完成并记录真实证据；最终修正保持矛盾状态、拒绝过期/已确认重投和页面版本一致性，受影响验收通过。B-02.1～.5已收口。此次.5为高：身份与版本竞态、真实A隐私/资格/价格校验、自动试算与登录返回、故障和页面联合验收；按第14节四步完成，D17/D18用户选择已落实，实际核心/页面与受影响回归均通过。B-02.6已按第15节三步完成实际联合验收与交接，复杂度中等：复用已完成业务与测试，补齐跨进程恢复、统一证据和字段交接。B-02.1～.6全部完成，B-03尚未开展。

## 17. B-02文件管理优化（2026-10-09）

### 17.1 范围、选择和实施

用户指定工作树 `D:/Java/zj-market-b02-noFileUpdate` 与分支 `b02-noFileUpdate`，从 master 的 dd59938 建立。D19/D20 已确认并落实；10月8日按用户要求保存暂停，10月9日收到“恢复工作”继续。本轮不开展 B-03，保持当前业务、数据库和固定运行组合。

七模块边界、接口/实现、独立公开模型、DAO/PO、仓储/技术适配、app 装配及前端分类见 [文件规范](project-layout.md)，真实架构取舍见 [ADR-0001](adr/0001-domain-service-module-layout.md)。恢复时将 trigger 配置类归回 trigger/config，验收入口改为读取当前工作树的 HTTP 契约。原外部 DPAPI 数据库凭据和学习 RSA 密钥仅复制到被忽略的 .local 供验收使用，没有写入源码。

### 17.2 结构与构建检查

105 个 Java 文件包路径检查通过，顶层接口/实现混合目录为0，七模块依赖图无环。与 HEAD 比较，Java 字符串常量数量及内容保持，SQL 字符串保持；11个配置/迁移/HTTP契约/前端锁文件去除Git行尾差异后内容一致。证据：target/layout-audit.json。此检查支持结构变更审查，不替代真实链路验收。

固定 JDK21 执行 `./scripts/mvn.ps1 -MavenArguments @('-B','-o','package')` 通过；原15项测试无失败/错误/跳过，复编证据 target/layout-resume-build.log 与 app/target/surefire-reports。前端离线安装、TypeScript6.0.3类型检查及Vite8.3.3构建通过，证据 target/layout-frontend-install.log、layout-frontend-build.log。

### 17.3 真实复验与收口

目录优化已完成。本轮真实联合验收批次 `layout-20261009-110821`，[总报告](../target/acceptance/layout-20261009-110821/report.json)为 PASSED，采用当前工作树的既有 B-02.6 入口复验，构建使用上一节刚完成的结果，所以联合命令带 -SkipBuild；不混用历史批次。

| 本轮检查 | 实际结果与证据（当前工作树） |
| --- | --- |
| 七模块及15项测试 | JDK21.0.2构建成功、15项无失败/错误/跳过；target/layout-resume-build.log、layout-audit.json |
| 双B库迁移和权限 | 已有V1～V4校验通过、无新增迁移；运行账号DDL/history/A/system/grant拒绝，迁移账号跨库/系统/全局DDL/grant拒绝；联合目录development/b02-test-migrate/verify.txt |
| HTTP和正常应用页面 | 注册/登录/轮换/撤销/用户与运营权限、商品版本/事务、可靠同步页面通过；联合目录identity/products/sync-browser.txt；实际运行普通app包 |
| 可靠同步与恢复 | 真实A签名结果、故障补查、重复/乱序/隔离、独立死信恢复；ACK前退出后新进程同回执、Inbox一条、确认状态保持，业务重试8次不变；target/sync/layout-20261009-110821-sync/verify.txt、ack-recovery.txt |
| A试算与在线/离线浏览器 | 自动/手动试算、身份与并发版本、真实60秒刷新上限、A停止后的页面与服务错误通过；target/trial/layout-20261009-110821-trial/verify/browser/browser-offline/offline.txt |
| 原中间件基线 | 合法RPC NOT_FOUND、错签AUTH_INVALID、MQ SEND_OK/VERIFIED_APPLIED、持久结果PROCESSED_APPLIED、订阅AUTHORIZED、越权发布PERMISSION_DENIED；target/environment-probe/layout-20261009-110821-baseline/report.json |
| 正常包、契约与环境 | 正常包无verification/Flyway；18操作及316本地引用有效；环境变更0、自有端口全部释放，默认Java8；产物SHA256载于总报告 |

复现时在此工作树运行（.local外部配置准备和共享服务要求与第15节一致；新RunName不覆盖原证据）：

```powershell
./scripts/mvn.ps1 -MavenArguments @('-B','-o','package')
$run = 'layout-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
./docs/tests/run-b02-acceptance.ps1 -RunName $run -SkipBuild
```

最后检查：本轮未忽略源码/文档与待提交候选中的11项已知实际秘密无命中，完整私钥/令牌命中为0，已跟踪但应忽略文件为0；.local与构建/前端产物继续忽略。证据 target/layout-safety.json，仅覆盖当前检查范围。主目录 master 与旧 b-02 工作树均保持干净；当前分支仍为 b02-noFileUpdate、HEAD dd59938，成果未提交，未合并或推送本轮变化。SQL/HTTP形状/事务与版本行为通过上述检查及实际验收保持，不改A源码、不升级或降级框架。IDE应打开当前根pom.xml并重新加载Maven；图形IDE和Docker中的B运行本轮未实测。

此次复杂度高：模块/模型迁移、配置装配与后台生命周期相互关联。已按结构审查、实际复验、规范与过程记录三步完成；B-02业务范围保持，B-03尚未开展。

### 17.4 本地提交归档（2026-10-09）

用户授权将本工作树成果提交到 b02-noFileUpdate。本次归档包含第17节已完成并验收的文件管理优化与全部配套文档；第17.3节未提交记录为归档前状态。本轮仅本地提交，不合并主分支、不推送远程；提交号以分支Git日志为准。提交前再次检查真实秘密与忽略边界，保留本地外部凭据及被忽略的构建/验收证据。

## 18. 三项评审补修（2026-10-09）

### 18.1 用户选择、修复与回归

用户指出P1多标签页旧JWT与共享新刷新Cookie退出漏撤销、P2成功发送写回锁等待跨租约以及P2签名消息尾随JSON/版本截断。D21由用户确认：同时撤销两份凭据对应登录，随后清Cookie；不同grant在同事务按稳定顺序撤销，同grant去重。HTTP形状保持，退出语义和机器契约说明同步补充。

IdentityService分别解析两份凭据，不再优先JWT而跳过Cookie；无效/过期凭据不阻止另一凭据退出。ProductSyncRepository.sent与失败/补查统一product→outbox行锁，获得锁后读取数据库时间，由原SQL检查租约、令牌及处理状态。SyncResultReader仍先验原字节签名，再拒绝尾随JSON/内容；schemaVersion必须为整数字面值且BigInteger精确等于1，禁止截断/浮点或字符串转换；坏消息仍先持久隔离，保存故障抛出以便MQ重试。

新增5项退出与6项解码JUnit：修复前26项中的5项失败，准确覆盖漏撤销、尾随内容、溢出及错误隔离行为；修复后26项全部通过，固定JDK21七模块打包通过。日志target/b02-review-before.log、b02-review-after.log，不把修复前失败误报为当前失败。

真实验收补入：同账号/不同账号JWT与共享Cookie、两份JWT失效、其他独立登录保持、双撤销第二次失败的MySQL事务回滚；Edge两标签切换账号再从旧标签退出；有效签名的尾随对象/4294967297/更大整数持久隔离；真实两连接持有Outbox行锁，发送写回等待跨过数据库租约期限，过期令牌不得写回，重新认领的新令牌可成功。锁等待测试只观察生产DAO调用并复用生产事务/SQL，不返回模拟数据库结果；全部故障入口限于verification或测试文件。

### 18.2 实际验收与当前状态

三项补修均完成。本轮批次 `review-20261009-115312`，[联合报告](../target/acceptance/review-20261009-115312/report.json)与[定向证据索引](../target/acceptance/review-20261009-115312/review-evidence.json)为 PASSED；新增回归结果均来自修复后的真实运行。

| 本轮验收 | 实际结果与当前工作树证据 |
| --- | --- |
| 26项JUnit/七模块JDK21构建 | 全部通过，无失败/错误/跳过；联合目录build.log、junit/；修复前5项失败保留于pre-fix-tests.log |
| P1双凭据退出 | 同账号和不同账号各两份JWT退出后均401，共享刷新Cookie清除，未提供凭据的其他登录保持；第二次撤销失败时真实MySQL回滚两次更新；联合目录identity-review.txt |
| P1多标签页 | Edge共享浏览器上下文；标签二注册/登录不同账号更新Cookie，标签一仍用原JWT成功读取本人，再退出；两份已签发JWT均401，Cookie清除，页面退出广播通过；联合目录identity-browser.txt |
| P2发送写回租约 | 两条真实MySQL连接：持行锁、写回阻塞、数据库租约到期后释放；读取时间晚于期限，未标记PUBLISHED也未清除旧租约令牌；新认领令牌可写回；target/sync/review-20261009-115312-sync/verify.txt |
| P2非法结构 | JUnit覆盖尾随对象/数组/标量/垃圾文本、溢出和超大/负值/浮点/字符串版本、合法尾随空白、先验签及隔离失败重试；真实签名尾随对象/4294967297/更大整数进入MySQL隔离，未应用结果；同一sync报告及本轮JUnit |
| 既有业务和集成 | 原商品版本/事务、同步/ACK重启、真实A试算、在线/离线浏览器、RPC/MQ/签名/ACL、双B库迁移及最小权限均通过；18HTTP操作/316引用有效，普通包无verification/Flyway |
| 环境和边界 | 调用方环境变更0，自有端口释放，默认Java8保持；双B库新增迁移0，依赖版本不变；总报告含当前产物SHA256 |

复现命令（只用既有隔离环境，每次使用新的RunName）：

```powershell
./scripts/mvn.ps1 -MavenArguments @('-B','-o','package')
$run = 'review-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
./docs/tests/run-b02-acceptance.ps1 -RunName $run -SkipBuild
```

这是业务缺陷补修，覆盖第17节目录整理时保持行为的历史结论中上述三处行为；不改变HTTP字段/响应结构、数据库迁移、依赖版本或A源码。锁等待回归使用短期测试租约并等待真实数据库时间，不伪称修复前已完成MySQL并发复现，也不增加生产故障开关。所有回归辅助类只在verification/测试中，正常包边界已经复查。最后敏感内容与忽略检查通过；当前HEAD仍d9f12c7，补修改动未提交、合并或推送。复杂度中等，已按复现、修复、实际联合复验和文档收口完成。

### 18.3 补修本地提交归档（2026-10-09）

用户已授权将第18节三项补修、回归测试、D21与配套文档提交至b02-noFileUpdate。此前未提交描述为授权前状态；提交标识以该分支Git日志为准。复用review-20261009-115312的实际PASSED证据及26项测试结果，本次归档不重复运行或冒称新增业务验收。提交前复查敏感信息和暂存范围；本轮仅本地提交，不合并或推送。

### 18.4 主分支合并与远程归档（2026-10-09）

用户授权合并至主分支并推送远程。master已从dd59938快进至f93c861，包含目录整理d9f12c7及三项补修f93c861；主目录D:/Java/zj-market现有七模块布局与修复。此前本轮未合并/推送的描述为当时状态。归档目标为origin/master（https://github.com/zjing-259/zj-market-B.git），最终远程提交以推送后Git核对为准。

本次合并不改变业务实现，沿用review-20261009-115312的PASSED及26项测试结果，没有重复执行业务验收。实际复验产物仍位于D:/Java/zj-market-b02-noFileUpdate/target/acceptance/review-20261009-115312，被忽略的本机凭据和产物不随Git合并/上传；不能把主目录没有该批次产物误认为已经在那里重跑。推送前再次核对实际秘密/私钥/令牌命中0，已跟踪但应忽略0。

## 2026-10-10历史状态校正复杂度

此次文档维护复杂度低：依据Git归档修正当前入口并明确历史实施范围，保留原验收批次、路径和指纹；未改变业务规则或重新执行业务验收。后续详细过程维护于 [B-04开发过程](b04-development.md)，总体进度同步[路线图](development-roadmap.md)。
