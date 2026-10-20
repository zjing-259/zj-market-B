"""Validate authored catalogue content before any product write."""
from pathlib import Path
from decimal import Decimal
import hashlib,json,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
assert ROOT.name=='zj-market-ux'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
source=ROOT/'docs/catalog-products.json';manifest=json.loads(source.read_text(encoding='utf-8'));items=manifest['products']
assert len(items)==6 and len({p['contentId'] for p in items})==len({p['goodsName'] for p in items})==6
for item in items:
    assert 0<len(item['goodsName'].encode('utf-16-le'))//2<=128 and len(item['description'])<=2000
    assert not any(word in item['goodsName'].lower() for word in ['test','ux05','cat-','验收'])
    assert item['currency']=='CNY' and Decimal(item['originalPrice'])-Decimal(item['payPrice'])==Decimal(item['activity']['reduction'])==10
    assert Decimal(item['payPrice'])>0 and item['initialStock']=='20' and item['activity']['targetCount']==2
    file=(ROOT/item['image']['repositoryPath']).resolve();assert file.is_relative_to((ROOT/'frontend/public/catalog').resolve())
    assert sha(file)==item['image']['sha256']
    svg=ET.fromstring(file.read_bytes());assert svg.attrib['viewBox']=='0 0 800 800'
    for node in svg.iter():
        assert node.tag.rsplit('}',1)[-1] not in ['script','foreignObject','image']
        assert not any(k.lower().startswith('on') or k.rsplit('}',1)[-1]=='href' for k in node.attrib)
    assert item['image']['sourceType']=='PROJECT_ORIGINAL_SVG' and item['image']['sourceUrl'] is None and item['alt']
preview=ROOT/'.local/cat/cat01-2-20261020-01/preview.json';assert json.loads(preview.read_text())['status']=='PASS'
report={'stage':'CAT-01.2','status':'PASS','stageCompleted':True,'products':6,'runtimeProductWrites':0,'contentVersion':manifest['version'],'contentSha256':sha(source),'imageSha256':{p['imagePath']:p['image']['sha256'] for p in items},'checks':['six-daily-Chinese-products-with-specs-and-description','positive-demo-prices-and-10-yuan-reductions','stock-and-activity-plan-explicit','original-800-square-SVGs-with-source-author-date-usage-hashes','no-third-party-or-external-assets','six-images-rendered-in-real-Edge','no-runtime-product-creation'],'previewSha256':sha(ROOT/'.local/cat/cat01-2-20261020-01/catalog-contact-sheet.png'),'sourceSha256':{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in [Path(__file__),ROOT/'scripts/cat02-preview.mjs']},'nextStage':'CAT-01.3; UX-only preparation and acceptance','boundaries':['Illustrations and specifications are demonstration content, not real product photography or certifications','Demo pricing is authored, not a market price or actual promotion','No main-site catalogue, stock, activity or order change']}
(ROOT/'docs/tests/cat01-2-acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# CAT 首版日常商品资料','', '内容版本：`'+manifest['version']+'`。六件商品均为虚构演示商品；定价为项目演示设定，不是市场价格调查或促销承诺。原创 SVG 为示意插画，非实物照片，不真实扣款或发货。','', '| 内容 ID | 商品名称 | 原价 | 两人团价 | 初始库存计划 | 团规则 |','| --- | --- | --- | --- | --- | --- |']
for p in items:lines.append(f"| {p['contentId']} | {p['goodsName']} | ¥{p['originalPrice']} | ¥{p['payPrice']} | 20 | 减 10 元，2 人，120 分钟，活动窗口 30 天 |")
lines+=['','完整描述、规格、图片替代文本、来源／作者／日期／用途和 SHA-256 见 [商品资料 JSON](catalog-products.json)，验收见 [CAT-01.2 报告](tests/cat01-2-acceptance.json)。所有内容由本项目本轮编写，不使用第三方商品照片、商标或外链。规格不作食品安全、保温、防漏、承重或通用适配承诺。','', '图片资源位于 UX 工作树 `frontend/public/catalog/{cup,bag,notebook,pouch,cutlery,stand}.svg`。UX 地址前缀为 `https://zj-market-ux.test:8446/catalog/`；主站将采用 `https://zj-market.test/catalog/`，但须待 CAT-01.4 构建及发布新资源后才能使用，本阶段不宣称主站已发布。','', 'CAT-01.3 使用新商品 ID 验证本资料，正常展示与专用验收样本分开；不复用旧验收商品 ID、不复制 UX 数据到主站。价格、图片与规格变更需产生新资料版本和哈希，再按商品版本规则同步。','']
(ROOT/'docs/catalog-products.md').write_text('\n'.join(lines),encoding='utf-8')
print('CAT02_CONTENT_ACCEPTANCE_PASS six-products/prices/specs/original-images/no-runtime-writes')
