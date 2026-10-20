// Main read-only acceptance. Never confirms a purchase or creates/pays/cancels an order.
import fs from 'node:fs'
import path from 'node:path'
import {createRequire} from 'node:module'
import {root,work,origin,fixture,content,Client,accounts,hash,save,load} from './cat04-products.mjs'
const f=fixture();if(f.phase!=='RETIRED')throw Error('Complete exact retirement first')
const c=new Client();await c.login();const all=await c.listing(),publicGoods=await c.listing('/products'),ids=new Set(publicGoods.map(x=>x.goodsId)),retired=new Set(f.retire.map(x=>x.goodsId)),census=load(path.join(root,'docs/cat01-product-inventory.json'))
if(all.length!==60||publicGoods.length!==8||f.retire.some(x=>ids.has(x.goodsId))||census.retainIds.some(x=>!ids.has(x))||f.items.some(x=>!ids.has(x.goodsId)))throw Error('Final public/admin catalogue differs')
for(const item of f.retire){const p=await c.api('/admin/products/'+item.goodsId);if(p.saleStatus!=='OFF_SALE'||!p.syncReady)throw Error('Retired item sync incomplete')}
const {chromium}=createRequire(path.join(root,'frontend/package.json'))('playwright-core'),browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',args:['--host-resolver-rules=MAP zj-market.test 127.0.0.1','--no-proxy-server']})
const report={stage:'CAT-01.4',status:'RUNNING',httpsBypass:false,checks:[],businessWrites:0,readOnlyTrials:0,publicGoods:publicGoods.map(x=>x.goodsId),retiredCount:52,retainedIds:census.retainIds,screenshots:[],originalOrders:[],pageErrors:[]}
const before=load(path.join(work,'main-before.json')),originalIds=new Set(before.orders.map(x=>x.order_id))
try{
 for(const key of ['b06buyer','b06buyer2']){
  const ctx=await browser.newContext({ignoreHTTPSErrors:false,viewport:{width:1440,height:900}}),page=await ctx.newPage();let token
  page.on('pageerror',e=>report.pageErrors.push(e.message))
  page.on('response',async r=>{if(/\/auth\/(login|refresh)$/.test(r.url())&&r.status()===200)token=(await r.json()).data.accessToken})
  page.on('request',r=>{if(['POST','PUT','PATCH','DELETE'].includes(r.method())&&r.url().startsWith(origin+'/api/')&&!r.url().includes('/auth/')){if(r.method()==='POST'&&/\/products\/[^/]+\/trial$/.test(r.url()))report.readOnlyTrials++;else report.businessWrites++}})
  await page.goto(origin+'/login');await page.getByLabel('登录名').fill(accounts[key].loginName);await page.getByLabel('密码',{exact:true}).fill(accounts[key].password);await page.locator('form button[type=submit]').click();await page.getByRole('button',{name:'退出登录',exact:true}).waitFor()
  if(!await page.evaluate(()=>isSecureContext&&!!navigator.locks))throw Error('Browser HTTPS not trusted')
  const read=async route=>page.evaluate(async({route,token})=>{const r=await fetch('/api/v1'+route,{headers:{Authorization:'Bearer '+token}});return {status:r.status,payload:await r.json()}},{route,token})
  let checked=0
  for(let pg=1;pg<100;pg++){
   const r=await read('/orders?page='+pg+'&size=20');if(r.status!==200||r.payload.code!=='0000')throw Error('Original order listing failed')
   for(const o of r.payload.data.items){if(!originalIds.has(o.orderId))throw Error('Unexpected new order');if(!retired.has(o.product.goodsId))continue;const detail=await read('/orders/'+o.orderId);if(detail.status!==200||detail.payload.code!=='0000')throw Error('Off-sale original order not readable');report.originalOrders.push({orderId:o.orderId,status:detail.payload.data.status});checked++;if(checked===2)break}
   if(checked===2||pg*20>=r.payload.data.total)break
  }
  if(checked<1)throw Error('No original retired sample order checked for buyer')
  await page.goto(origin+'/orders/'+report.originalOrders.at(-1).orderId);await page.getByRole('heading',{name:'订单详情',exact:true}).waitFor();report.checks.push('original-off-sale-order-readable-'+key)
  if(key==='b06buyer'){
   for(const p of content.products){const r=await page.goto(origin+p.imagePath);if(r.status()!==200||!r.headers()['content-type'].includes('image/svg+xml'))throw Error('Image not served');const temp=path.join(work,p.key+'-served.svg');fs.writeFileSync(temp,await r.body());if(hash(temp)!==p.image.sha256)throw Error('Runtime image hash differs');report.checks.push('runtime-image-'+p.key)}
   for(const width of [360,390,1280,1440]){
    await page.setViewportSize({width,height:900});await page.goto(origin+'/products');await page.getByRole('heading',{name:'在售商品',exact:true}).waitFor()
    for(const p of content.products){const tile=page.locator('.product-tile').filter({has:page.getByRole('heading',{name:p.goodsName,exact:true})});await tile.waitFor();await tile.locator('img').evaluate(i=>i.decode());if(!await tile.locator('img').evaluate(i=>i.naturalWidth>0))throw Error('Image failed');if(!(await tile.textContent()).includes(p.originalPrice))throw Error('List price differs')}
    if(!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))throw Error('Catalogue overflow');const shot='main-showcase-'+width+'.png';await page.screenshot({path:path.join(work,shot),fullPage:true});report.screenshots.push({file:shot,sha256:hash(path.join(work,shot))})
    const item=f.items[0];await page.goto(origin+'/products/'+item.goodsId);await page.getByText('拼团实付 ¥ '+item.payPrice,{exact:true}).waitFor();if(!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))throw Error('Product detail overflow');await page.screenshot({path:path.join(work,'main-detail-'+width+'.png'),fullPage:true})
   }
   for(const item of f.items){await page.goto(origin+'/products/'+item.goodsId);await page.getByText('拼团实付 ¥ '+item.payPrice,{exact:true}).waitFor();await page.getByText(item.fields.description,{exact:true}).waitFor();await page.getByRole('button',{name:'单独开团',exact:true}).waitFor();if(!await page.getByRole('button',{name:'单独开团',exact:true}).isEnabled())throw Error('Expected offer unavailable');report.checks.push('actual-product-description-price-availability-'+item.key)}
   // Keep probe/no-image legacy item: existing fallback must remain understandable.
   await page.goto(origin+'/products');const legacy=page.locator('.product-tile').filter({has:page.getByRole('heading',{name:'B06 demonstration product',exact:true})});await legacy.waitFor();if(!await legacy.locator('.image-placeholder').isVisible())throw Error('Legacy placeholder missing');report.checks.push('retained-probe-image-placeholder')
  }
  await ctx.close()
 }
 if(report.businessWrites||report.pageErrors.length)throw Error('Read-only browser wrote or had page errors')
 report.status='PASS';save(path.join(work,'browser-report.json'),report);console.log('CAT04_BROWSER_PASS 6-daily/52-off-sale/2-retained/4-viewports/original-orders-readable/no-trades')
}catch(e){report.status='FAIL';report.error=e.message;save(path.join(work,'browser-report.json'),report);throw e}finally{await browser.close()}
