# CAT 首版日常商品资料

内容版本：`cat-content-20261020-01`。六件商品均为虚构演示商品；定价为项目演示设定，不是市场价格调查或促销承诺。原创 SVG 为示意插画，非实物照片，不真实扣款或发货。

| 内容 ID | 商品名称 | 原价 | 两人团价 | 初始库存计划 | 团规则 |
| --- | --- | --- | --- | --- | --- |
| CAT-S01 | 雾蓝随行杯 | ¥39.90 | ¥29.90 | 20 | 减 10 元，2 人，120 分钟，活动窗口 30 天 |
| CAT-S02 | 原色帆布袋 | ¥29.90 | ¥19.90 | 20 | 减 10 元，2 人，120 分钟，活动窗口 30 天 |
| CAT-S03 | 方格随手本 | ¥19.90 | ¥9.90 | 20 | 减 10 元，2 人，120 分钟，活动窗口 30 天 |
| CAT-S04 | 拉链收纳袋 | ¥24.90 | ¥14.90 | 20 | 减 10 元，2 人，120 分钟，活动窗口 30 天 |
| CAT-S05 | 便携餐具盒 | ¥35.90 | ¥25.90 | 20 | 减 10 元，2 人，120 分钟，活动窗口 30 天 |
| CAT-S06 | 折叠手机支架 | ¥29.90 | ¥19.90 | 20 | 减 10 元，2 人，120 分钟，活动窗口 30 天 |

完整描述、规格、图片替代文本、来源／作者／日期／用途和 SHA-256 见 [商品资料 JSON](catalog-products.json)，验收见 [CAT-01.2 报告](tests/cat01-2-acceptance.json)。所有内容由本项目本轮编写，不使用第三方商品照片、商标或外链。规格不作食品安全、保温、防漏、承重或通用适配承诺。

图片资源位于 UX 工作树 `frontend/public/catalog/{cup,bag,notebook,pouch,cutlery,stand}.svg`。UX 地址前缀为 `https://zj-market-ux.test:8446/catalog/`；主站已由 CAT-01.4 发布到 `https://zj-market.test/catalog/`，运行资源哈希已核对。

CAT-01.3 使用新商品 ID 验证本资料，正常展示与专用验收样本分开；不复用旧验收商品 ID、不复制 UX 数据到主站。价格、图片与规格变更需产生新资料版本和哈希，再按商品版本规则同步。

CAT-01.3 UX 实际展示商品（与下方主站新 ID 独立）：

| 内容 ID | 名称 | UX 商品 ID | 详情 |
| --- | --- | --- | --- |
| CAT-S01 | 雾蓝随行杯 | `28f891db-2bf3-4210-b13e-0ad29eafdd6d` | [UX 商品页](https://zj-market-ux.test:8446/products/28f891db-2bf3-4210-b13e-0ad29eafdd6d) |
| CAT-S02 | 原色帆布袋 | `1a93009a-d318-46ca-ae9d-6b4112264153` | [UX 商品页](https://zj-market-ux.test:8446/products/1a93009a-d318-46ca-ae9d-6b4112264153) |
| CAT-S03 | 方格随手本 | `9d0311e3-8164-42a8-aa5f-07ffafc27bfd` | [UX 商品页](https://zj-market-ux.test:8446/products/9d0311e3-8164-42a8-aa5f-07ffafc27bfd) |
| CAT-S04 | 拉链收纳袋 | `3cc36149-b95b-4181-8914-b0dffc55508c` | [UX 商品页](https://zj-market-ux.test:8446/products/3cc36149-b95b-4181-8914-b0dffc55508c) |
| CAT-S05 | 便携餐具盒 | `a9fe54ef-d12b-417a-bc47-f022ec12dede` | [UX 商品页](https://zj-market-ux.test:8446/products/a9fe54ef-d12b-417a-bc47-f022ec12dede) |
| CAT-S06 | 折叠手机支架 | `306ecfa3-ce91-4cf2-8e1b-a26b99498d9d` | [UX 商品页](https://zj-market-ux.test:8446/products/306ecfa3-ce91-4cf2-8e1b-a26b99498d9d) |

以上六件在 UX 最终均为 ON_SALE 且当前版本同步确认，各库存 20、无本批新订单。八件专用验收商品最终均 OFF_SALE；详见 [运行商品清单](cat03-ux-products.json)。本批仅验证 UX，不将旧 UX 验收商品一并下架，也不替代 CAT-01.4 主站整理。

CAT-01.4 主站实际展示商品（各 20 可用库存，版本 2，A 已确认；本阶段无新订单）：

| 内容 ID | 商品 | 主站商品 ID | 详情 |
| --- | --- | --- | --- |
| CAT-S01 | 雾蓝随行杯 | `68d2db7c-62d8-402b-a52a-ea1e6bca93dc` | [主站商品页](https://zj-market.test/products/68d2db7c-62d8-402b-a52a-ea1e6bca93dc) |
| CAT-S02 | 原色帆布袋 | `d42cd30c-4438-47d9-bfe1-1657f2864b3a` | [主站商品页](https://zj-market.test/products/d42cd30c-4438-47d9-bfe1-1657f2864b3a) |
| CAT-S03 | 方格随手本 | `830a2bc3-e828-480b-abd9-96571a1097dc` | [主站商品页](https://zj-market.test/products/830a2bc3-e828-480b-abd9-96571a1097dc) |
| CAT-S04 | 拉链收纳袋 | `a86372f0-c65e-4c95-9610-643343b8047e` | [主站商品页](https://zj-market.test/products/a86372f0-c65e-4c95-9610-643343b8047e) |
| CAT-S05 | 便携餐具盒 | `f343b1e1-da5f-4207-a835-b9222321c574` | [主站商品页](https://zj-market.test/products/f343b1e1-da5f-4207-a835-b9222321c574) |
| CAT-S06 | 折叠手机支架 | `0527e161-8ca8-4744-ba24-fd886536e5cf` | [主站商品页](https://zj-market.test/products/0527e161-8ca8-4744-ba24-fd886536e5cf) |

精确活动区间、库存和状态见 [主站运行清单](cat04-main-products.json)，证据见 [CAT-01.4](tests/cat01-4-acceptance.json)。主站后续交易验收使用 CAT-01.5 专用样本，日常六件主要只读检查。
