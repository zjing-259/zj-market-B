---
status: accepted
---

# 对齐 A 的模块边界，业务服务归 domain

2026-10-08，用户在 D19 选择对齐 group-buy-market 的模块边界，在 D20 选择现有业务服务建立 I*Service，实现放独立子目录。B 因此新增 api/types、移除 application，将用例协调与业务端口归 domain；API DTO 和共享异常分别归 api/types，基础设施实现、入站触发及 app 装配各自分离，便于按 A 的目录习惯定位接口与实现。

原 application 独立用例层改为 domain.service/service.impl，代价是 domain 同时包含模型与业务协调；通过纯 Java 模型、出站接口和 Maven 依赖约束保持其不依赖 Spring/A SDK。B 的 verification 是独立验收包，继续保留，避免为机械对齐 A 而将迁移或故障测试加入普通启动。此决定只调整代码组织，HTTP、事务、事件和版本规则保持。
