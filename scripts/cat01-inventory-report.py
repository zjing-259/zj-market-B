"""Cross-check live GET inventory and read-only SQL; publish exact-ID review lists."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import argparse,hashlib,json

ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def index(rows,key='goods_id'):return {x[key]:x for x in rows}
def counts(rows,key):return dict(sorted(Counter(x[key] for x in rows).items()))
def main():
 p=argparse.ArgumentParser();p.add_argument('--batch',required=True);args=p.parse_args()
 import re
 assert ROOT.name=='zj-market-ux' and re.fullmatch(r'cat01-1-[0-9]{8}-[0-9]{2}',args.batch)
 work=ROOT/'.local/cat'/args.batch/'main'
 data=load(work/'before.json')['zj-market-b06'];api=load(work/'api-inventory.json');ownership=load(work/'ownership.json');proof=load(work/'read-only-proof.json');environment=load(work/'environment.json')
 assert proof['status']=='PASS' and api['strictTLS'] and api['resourceWrites']==0
 assert all(x['before']==x['after'] for x in proof['checks'].values())
 assert environment['status']=='PASS' and environment['stable']['status']=='READY' and environment['uxGate']=='UX_GATE_OPEN' and environment['isolation']['status']=='PASS'
 assert all(x['status']==200 and x['code']=='0000' and x['tlsAuthorized'] and (x['method']=='GET' or x['method']=='POST' and x['route']=='/auth/login') for x in api['requests'])
 products=index(data['products']);inventory=index(data['inventory']);sync=index(data['sync'])
 details={x['product']['goodsId']:x for x in api['details']}
 assert set(products)==set(details)=={x['goodsId'] for x in api['adminListing']['items']}
 assert {k for k,v in products.items() if v['sale_status']=='ON_SALE'}=={x['goodsId'] for x in api['publicListing']['items']}
 projections={(x['source'],x['channel'],x['goods_id']):x for x in data['projection']}
 activities=index(data['activities'],'activity_id');discounts=index(data['discounts'],'discount_id')
 orders=index(data['orders'],'order_id');records=[]
 now=datetime.now(timezone.utc);sources=ownership['products'];seed=ownership['seed']['goodsId']
 for goods,product in sorted(products.items()):
  detail=details[goods];a=detail['product'];stock=inventory[goods];s=sync[goods]
  for db,key in [('goods_name','goodsName'),('description','description'),('image_url','imageUrl'),('currency','currency'),('sale_status','saleStatus')]:assert product[db]==a[key]
  from decimal import Decimal
  assert Decimal(str(product['original_price']))==Decimal(a['originalPrice'])
  assert str(product['product_version'])==a['productVersion']
  assert all(str(stock[key])==detail['inventory'][key] for key in ['available','reserved','sold'])
  assert str(stock['inventory_version'])==detail['inventory']['version']
  assert str(s['target_version'])==detail['sync']['targetVersion'] and str(s['confirmed_version'])==detail['sync']['confirmedVersion'] and s['state']==detail['sync']['state']
  projection=projections.get(('b06','web',goods))
  confirmed=s['state']=='CONFIRMED' and s['confirmed_version']==s['target_version']==product['product_version']
  assert a['syncReady']==confirmed
  if confirmed:assert projection and projection['product_version']==product['product_version'] and projection['sale_status']==product['sale_status'] and Decimal(str(projection['original_price']))==Decimal(str(product['original_price'])) and projection['goods_name']==product['goods_name']
  own=sources.get(goods,[])
  if goods==seed:category,action='DEMO_RETAIN','KEEP_PROBE_DEPENDENCY'
  elif own:category,action='CONFIRMED_ACCEPTANCE','OFF_SALE_CANDIDATE_AFTER_REPLACEMENT'
  else:category,action='UNRESOLVED_RETAIN','KEEP_PENDING_OWNERSHIP_REVIEW'
  related=[x for x in data['orders'] if x['goods_id']==goods];ids={x['order_id'] for x in related}
  teams=[x for x in data['teams'] if x['goods_id']==goods];payments=[x for x in data['payments'] if x['goods_id']==goods];refunds=[x for x in data['refunds'] if x['order_id'] in ids]
  work_items=[x for x in data['work'] if x['order_id'] in ids and x['state']!='DONE']
  blocks=[x for x in data['blocks'] if x['order_id'] in ids and x['state']=='ACTIVE']
  fulfillment=[x for x in data['fulfillment'] if x['goods_id']==goods and x['status']=='PENDING']
  bound=[]
  for binding in data['bindings']:
   if binding['goods_id']!=goods:continue
   activity=activities[binding['activity_id']];discount=discounts.get(activity['discount_id'])
   start=datetime.fromisoformat(activity['start_time']).replace(tzinfo=timezone.utc);end=datetime.fromisoformat(activity['end_time']).replace(tzinfo=timezone.utc)
   bound.append({**binding,'activity':activity,'discount':discount,'configuredWindowOpen':activity['status']==1 and start<=now<=end,'eligibilityAndQuoteVerified':False})
  issues=[]
  if not own and goods!=seed:issues.append('NO_EXACT_FIXTURE_OWNERSHIP_EVIDENCE')
  if goods==seed:issues.append('ACTIVE_READINESS_PROBE_REQUIRES_ON_SALE_PRODUCT')
  if any(t['team_status']=='RECONCILING' for t in teams):issues.append('A_RECONCILING_TEAMS_RETAIN_ORIGINAL_RECOVERY')
  if work_items:issues.append('HISTORICAL_UNFINISHED_WORK_REQUIRES_HANDOFF')
  if fulfillment:issues.append('PENDING_FULFILLMENT_IS_PRESERVED_NOT_FINANCIAL_FAILURE')
  if any(x['review_required'] for x in related):issues.append('ORDER_REVIEW_FLAGS_RETAINED')
  if not product['image_url']:issues.append('NO_PRODUCT_IMAGE')
  if not bound:issues.append('NO_ACTIVITY_BINDING')
  pending_payments=[x for x in payments if x['funds_state']=='UNKNOWN' or x['funds_state']=='SUCCEEDED' and x['a_acceptance']!='ACCEPTED' or x['funds_state']=='UNPAID' and x['gate']!='CLOSED_UNPAID']
  pending_refunds=[x for x in refunds if x['funds_status']!='SUCCEEDED' or x['sync_status']!='ACCEPTED' or x['release_status']!='RELEASED']
  records.append({'goodsId':goods,'product':product,'inventory':stock,'sync':s,'aProjection':projection,'classification':category,'proposedAction':action,'provenance':own if own else ([ownership['seed']] if goods==seed else []),'activities':bound,
    'orderStatusCounts':counts(related,'business_status'),'orders':related,'ongoingOrders':[x for x in related if x['business_status'] not in ['CLOSED','GROUP_COMPLETED']],
    'teamStatusCounts':counts(teams,'team_status'),'ongoingTeams':[x for x in teams if x['team_status'] in ['FORMING','RECONCILING']],
    'payments':payments,'refunds':refunds,'pendingFinancialPayments':pending_payments,'pendingFinancialRefunds':pending_refunds,'unfinishedWork':work_items,'activeBlocks':blocks,'pendingFulfillment':fulfillment,'issues':issues})
 proposal=[{'contentId':'CAT-S'+str(i).zfill(2),'name':name,'action':'CREATE_NEW_MAIN_PRODUCT','goodsId':None,'price':'TO_BE_FROZEN_IN_CAT_01_2','initialStock':'TO_BE_PLANNED','reuseScope':reuse} for i,(name,reuse) in enumerate([
  ('轻行随身杯','可参考 UX-04 原创杯子文案／插画，主站新建独立 ID，不复制 UX 数据'),('日常帆布袋','可参考 UX-04 原创帆布袋文案／插画，主站新建独立 ID，不复制 UX 数据'),('日常笔记本','CAT-01.2 新准备资料和图片'),('桌面收纳袋','CAT-01.2 新准备资料和图片'),('便携餐具套装','CAT-01.2 新准备资料和图片'),('桌面手机支架','CAT-01.2 新准备资料和图片')],1)]
 classified=counts(records,'classification');down=[x['goodsId'] for x in records if x['classification']=='CONFIRMED_ACCEPTANCE'];keep=[x['goodsId'] for x in records if x['classification']!='CONFIRMED_ACCEPTANCE']
 assert not set(down)&set(keep) and set(down)|set(keep)==set(products)
 assert all(sources.get(goods) for goods in down) and seed in keep
 summary={'products':len(records),'onSale':sum(x['product']['sale_status']=='ON_SALE' for x in records),'classificationCounts':classified,'inventoryTotals':{key:sum(x[key] for x in data['inventory']) for key in ['available','reserved','sold']},'syncedToCurrentA':sum(x['sync']['state']=='CONFIRMED' and x['sync']['confirmed_version']==x['product']['product_version'] for x in records),'orders':len(data['orders']),'orderStatusCounts':counts(data['orders'],'business_status'),'teamStatusCounts':counts(data['teams'],'team_status'),'pendingFinancialPayments':sum(len(x['pendingFinancialPayments']) for x in records),'pendingFinancialRefunds':sum(len(x['pendingFinancialRefunds']) for x in records),'unfinishedWork':sum(len(x['unfinishedWork']) for x in records),'activeBlocks':sum(len(x['activeBlocks']) for x in records),'reviewFlaggedOrders':sum(x['review_required'] for x in data['orders']),'pendingFulfillment':sum(len(x['pendingFulfillment']) for x in records),'missingImage':sum(not x['product']['image_url'] for x in records),'activityBindings':len(data['bindings'])}
 report={'stage':'CAT-01.1','status':'PASS_INVENTORY_ONLY','generatedAt':now.isoformat(),'batch':args.batch,'origin':'https://zj-market.test','scope':'read-only product census; no catalogue/stock/activity/order mutations','summary':summary,'candidateOffSaleIds':down,'retainIds':keep,'newProductProposals':proposal,'products':records,'pendingObligationsResolvedByThisStage':False,'rawEvidenceSha256':{name:sha(work/name) for name in ['before.json','after.json','ownership.json','api-inventory.json','read-only-proof.json','environment.json']}}
 save(ROOT/'docs/cat01-product-inventory.json',report)
 checks=['both-sites-ready-and-isolated','full-admin-and-public-pagination','unique-exact-goods-ids-match-sql','api-product-fields-and-versions-match-sql','api-stock-balances-and-versions-match-sql','sync-target-and-confirmed-version-match-A','exact-fixture-ownership-only-no-name-based-classification','active-probe-product-explicitly-retained','unknown-product-retained','ongoing-teams-financial-work-review-and-fulfillment-recorded','six-new-content-proposals-no-fabricated-goods-id','both-site-business-and-order-snapshot-digests-unchanged']
 acceptance={'stage':'CAT-01.1','status':'PASS','stageCompleted':True,'seriesCompleted':False,'generatedAt':now.isoformat(),'batch':args.batch,'checks':checks,'summary':summary,'pagination':{'admin':api['adminListing']['pages'],'public':api['publicListing']['pages']},'apiRequests':len(api['requests']),'strictTLS':True,'businessResourceWrites':0,'sqlTransactionsReadOnly':True,'identityLoginMayUpdateAuthState':True,'businessFactsUnchanged':True,'inventoryFile':'docs/cat01-product-inventory.json','inventorySha256':sha(ROOT/'docs/cat01-product-inventory.json'),'proofSha256':sha(work/'read-only-proof.json'),'sourceSha256':{str(f.relative_to(ROOT)).replace('\\','/'):sha(f) for f in [ROOT/'scripts/cat01-inventory.py',ROOT/'scripts/cat01-inventory-client.mjs',Path(__file__)]},'boundaries':['CAT-T01 inventory subset passed; later catalogue replacement/transaction/cleanup criteria remain unexecuted','No trial, new order, payment, refund, stock, activity or product mutation invoked by inventory tools','Active A reconciliation, historical deferred work, owned blocks and fulfillment records are observed and preserved; not repaired','Candidates are proposed IDs only. CAT-01.4 must re-read current versions/obligations and prepare usable replacements before taking anything off sale','Names are descriptive only; no name-pattern cleanup']}
 acceptance['environment']={'stable':environment['stable'],'uxGate':environment['uxGate'],'isolationChecks':environment['isolation']['checks'],'imageIds':environment['isolation']['imageIds']}
 acceptance['environmentEvidenceSha256']=sha(work/'environment.json')
 save(ROOT/'docs/tests/cat01-1-acceptance.json',acceptance)
 def esc(s):return str(s).replace('|','／').replace('\n',' ')
 lines=['# CAT-01.1 主站商品盘点清单','',f"盘点批次：`{args.batch}`；时间：`{now.isoformat()}`（UTC）。主站 `https://zj-market.test`。**只读盘点已验收，以下下架建议尚未执行。**",'',
 '完整字段及原始归属证据摘要见 [机器清单](cat01-product-inventory.json)，验收见 [CAT-01.1 报告](tests/cat01-1-acceptance.json)。执行前必须重读实时状态，本清单不是未来写入授权或固定版本保证。','',
 '## 1. 盘点结论','',f"共 {summary['products']} 件，全部在售；运营和商城列表均完整读取 {len(api['adminListing']['pages'])} 页。{len(down)} 件由明确 fixture 商品 ID 确认验收归属，列为替换后待下架候选；{len(keep)} 件保留（就绪探针演示商品、归属待核对商品各 1 件）。",'',
 f"当前 B 共 {summary['orders']} 笔订单：{summary['orderStatusCounts']}；库存可用／预留／已售为 {summary['inventoryTotals']['available']}/{summary['inventoryTotals']['reserved']}/{summary['inventoryTotals']['sold']}。全部 {summary['syncedToCurrentA']} 件已确认当前版本，53 条活动绑定；配置有效不等于已校验用户资格或实际优惠，本阶段不做 trial 或新交易。",'',
 f"A 团队状态为 {summary['teamStatusCounts']}。另保留 {summary['unfinishedWork']} 项历史未完成工作、{summary['activeBlocks']} 条 ACTIVE 归属隔离、{summary['reviewFlaggedOrders']} 笔 review 标记及 {summary['pendingFulfillment']} 条待履约；当前待资金确认／退款收尾均为 0。B CLOSED 不代表 A 核对记录已消失；这些记录未由本阶段修复。",'',
 f"{summary['missingImage']} 件未配置图片。全部商品均非已准备好的首版中文展示集；推荐 CAT-01.2 准备 6 件新商品，复用内容时仅复用有权使用的文案／图片，不复制 UX 数据库或商品 ID。",'',
 '## 2. 保留清单','', '| 商品 ID | 当前名称 | 原价／库存可用-预留-已售 | 处置原因 |','| --- | --- | --- | --- |']
 for x in records:
  if x['goodsId'] in keep:
   st=x['inventory'];reason='当前稳定发布 ready 探针依赖，须保持可读在售；不得作为验收样本清理' if x['goodsId']==seed else '未找到精确 fixture 证据；虽名称似验收样本，仍默认保留并待核对'
   lines.append(f"| `{x['goodsId']}` | {esc(x['product']['goods_name'])} | {x['product']['original_price']}／{st['available']}-{st['reserved']}-{st['sold']} | {reason} |")
 lines+=['','## 3. 待下架候选清单','', '仅在正常展示商品已就绪、当前版本及原义务重新核对后，通过运营接口处理；本表不执行操作。活动详情、描述／图片、原事件／版本和订单／团队 ID 均在机器清单逐件保留。','', '| 商品 ID | 当前名称 | v／原价 | 可用-预留-已售 | 活动 ID／团有效分钟 | B 订单状态计数 | A 核对中团队数 | fixture 批次 |','| --- | --- | --- | --- | --- | --- | --- | --- |']
 for x in records:
  if x['goodsId'] not in down:continue
  product=x['product'];st=x['inventory'];act='；'.join(str(y['activity_id'])+'/'+str(y['activity']['valid_time']) for y in x['activities']) or '无绑定'
  lines.append(f"| `{x['goodsId']}` | {esc(product['goods_name'])} | {product['product_version']}／{product['original_price']} | {st['available']}-{st['reserved']}-{st['sold']} | {act} | {esc(x['orderStatusCounts'])} | {x['teamStatusCounts'].get('RECONCILING',0)} | {esc(x['provenance'][0]['batch'])} |")
 lines+=['','## 4. 需交接的历史义务','', '进行中团队和历史核对／隔离按现有恢复规则保留；待履约是成团后的既有义务，不是本次新增失败。所有商品 ID 对应的完整记录在机器清单中，不能为清理首页强改这些记录。','', '| 商品 ID | A 进行中团队 | 未完成工作 | ACTIVE 隔离 | review 订单 | 待履约 |','| --- | --- | --- | --- | --- | --- |']
 for x in records:
  rv=sum(y['review_required'] for y in x['orders'])
  if x['ongoingTeams'] or x['unfinishedWork'] or x['activeBlocks'] or x['pendingFulfillment'] or rv:
   lines.append(f"| `{x['goodsId']}` | {len(x['ongoingTeams'])} | {len(x['unfinishedWork'])} | {len(x['activeBlocks'])} | {rv} | {len(x['pendingFulfillment'])} |")
 lines+=['','历史 DEFERRED_B05 项（仅记录，不重放）：','']
 for item in data['work']:
  if item['state']!='DONE':lines.append(f"- 工作 `{item['work_id']}`；订单 `{item['order_id']}`；团队 `{item['team_id']}`；类型 `{item['kind']}`，状态 `{item['state']}`。")
 lines+=['','## 5. 新商品清单（内容准备建议，未创建）','', '| 内容标识 | 建议名称 | 新建／复用范围 | 价格与库存 |','| --- | --- | --- | --- |']
 for x in proposal:lines.append(f"| {x['contentId']} | {x['name']} | 主站新建；{x['reuseScope']} | CAT-01.2 冻结，未创建商品 ID |")
 lines+=['','## 6. 验收与复用','', '盘点使用严格 TLS 的分页 GET，只有运营身份登录会更新认证状态；SQL 连接使用 READ ONLY 一致性事务。商品、同步语义、库存／流水、订单快照、资金、退款、团队、核对工作与履约的盘点前后摘要在两站一致。未修改运行镜像、容器、活动、商品或业务数据。','',
 f"工具：UX 工作树 `python -B scripts/cat01-inventory.py capture --batch {args.batch}` → `node scripts/cat01-inventory-client.mjs {args.batch}` → `python -B scripts/cat01-inventory.py verify --batch {args.batch}` → `python -B scripts/cat01-inventory-report.py --batch {args.batch}`。已保存批次禁止覆盖 capture；再次现场观察使用新批次，保留旧证据。私有原始证据位于 `.local/cat/{args.batch}/main`。",'',
 '本阶段只完成 CAT-01.1；CAT-01.2～01.5 仍待实施。后续不能把本次下架候选当已执行结果，也不能把历史义务计数硬编码为必须清零的验收条件。','']
 (ROOT/'docs/cat01-product-inventory.md').write_text('\n'.join(lines),encoding='utf-8')
 print('CAT01_INVENTORY_ACCEPTANCE_PASS '+json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()
