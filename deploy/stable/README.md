# ST-02 独立稳定版部署包

ST-02 的最终候选位于已忽略的 `target/stable-isolation/st02_20261016_04/bundle`。本阶段只生成与检查部署包，主站 `zj-market-b06` 仍由原控制入口运行；ST-03 完成一致性备份和受控接管前，不调用新入口的 `start`、`stop` 或 `open`。

部署包分为 `releases/td06-stable-20261016-01`（固定镜像、Compose 模板与工具）、`private`（37 份实际运行配置／证书／账号与哈希清单）和 `state`（可变 Compose 渲染、生命周期日志、浏览器资料）。镜像 tar 仍按 ST-01 清单保存在忽略的 `target/stable-isolation/st01_20261016_01/images`；ST-03 搬入独立目录时须连同镜像归档交付。私有目录仅授权当前用户、SYSTEM 和 Administrators，复制部署包后需重新收紧并核验 ACL。

部署包生成器从 TD-06 已验的 `compose-on.json`／`compose-maintenance.json`、ST-00 实际挂载与 ST-01 固定镜像清单取材，逐字节复制并校验私有输入，不覆盖已有批次。七个常驻服务和已退出的 MQ 权限辅助服务均固定实际 Image ID；五个原数据卷和五个网络声明为 `external: true`。运行模板只引用包内 `private`，没有 `build:`、源码挂载、旧工作树路径或自动 pull／迁移／旧备份恢复。旧备份原件继续保留；新启动门禁改用包内固定清单、原卷创建时间、网络 ID、schema／Flyway／索引和只读业务探针，不再调用旧备份控制器。

生成新批次时显式指定包根目录，例如：

```powershell
python -B scripts/stable-release/build-st02-bundle.py --root D:\Java\zj-market\target\stable-isolation\st02_new_batch\bundle
python -B scripts/stable-release/verify-st02-bundle.py D:\Java\zj-market\target\stable-isolation\st02_new_batch\bundle
```

当前包可只读查看状态：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Java\zj-market\target\stable-isolation\st02_20261016_04\bundle\releases\td06-stable-20261016-01\stable.ps1 -Action status
```

当前应显示 `adopted:false`。`ready` 必须拒绝尚未从新包接管的主站。ST-03 先做最新一致性备份、核验卷和待办义务，再由独立目录创建带备份批次与清单哈希的 `state/adoption.json`；此凭证只授权新控制器实施受控切换，不能替代备份及现场核验。`start` 对已接管且健康开放的主站仅检查并返回；前置失败不改网关。真正启动变更后失败才转维护或停止 web。`stop` 先核实维护模式再按依赖顺序停止服务，始终保留卷。`open` 仅在 `ready` 通过后用专属 Edge 配置目录打开严格 TLS 地址。

ST-02 本机验收见[摘要](../../docs/tests/st02-acceptance.json)。生命周期顺序和失败关门由无 Docker／浏览器调用的隔离测试覆盖；真实主站接管、停启与浏览器打开归 ST-03 联合验收。
