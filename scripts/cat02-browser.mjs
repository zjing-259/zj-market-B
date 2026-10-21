// Final catalogue in an anonymous browser; authenticated contexts read historical orders only.
import fs from 'node:fs'
import path from 'node:path'
import {createRequire} from 'node:module'
import {root,work,origin,targets,Client,accounts,load,hash,save} from './cat02-closeout.mjs'
const normal=load(path.join(root,'docs/cat04-main-products.json')).products,content=load(path.join(root,'docs/catalog-products.json')).products,c=new Client()
await c.login();const all=await c.pages('/admin/products'),publicGoods=await c.pages('/products')
if(all.length!==67||publicGoods.length!==6||normal.some(x=>!publicGoods.some(p=>p.goodsId===x.goodsId))||targets.some(x=>publicGoods.some(p=>p.goodsId===x)))throw Error('Final catalogue set differs')
for(const id of targets){const p=await c.api('/admin/products/'+id);if(p.saleStatus!=='OFF_SALE'||p.productVersion!=='2'||!p.syncReady)throw Error('Retirement/sync incomplete')}
const {chromium}=createRequire(path.join(root,'frontend/package.json'))('playwright-core'),browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',args:['--host-resolver-rules=MAP zj-market.test 127.0.0.1','--no-proxy-server']})
const report={status:'RUNNING',strictTLS:true,ignoreHTTPSErrors:false,publicGoods:publicGoods.map(p=>({goodsId:p.goodsId,goodsName:p.goodsName})),checks:[],originalOrders:[],blockedBusinessMutations:0,pageErrors:[],screenshots:{},normalProductInspection:'anonymous GET only; activity/stock/price invariants checked independently'}
async function context(){
 const ctx=await browser.newContext({ignoreHTTPSErrors:false,viewport:{width:1440,height:900}})
 await ctx.route(origin+'/api/v1/**',async route=>{const r=route.request(),p=new URL(r.url()).pathname;if(r.method()==='GET'||p.startsWith('/api/v1/auth/'))return route.continue();report.blockedBusinessMutations++;await route.abort('blockedbyclient')})
 const page=await ctx.newPage();page.on('pageerror',e=>report.pageErrors.push(e.message));return{ctx,page}
}
try{
 const {ctx,page}=await context()
 for(const asset of content){const r=await page.goto(origin+asset.imagePath);if(r.status()!==200||!r.headers()['content-type'].includes('image/svg+xml'))throw Error('Runtime image failed');const p=path.join(work,'served-'+asset.key+'.svg');fs.writeFileSync(p,await r.body());if(hash(p)!==asset.image.sha256)throw Error('Image content changed');report.checks.push('image-sha256-'+asset.key)}
 for(const width of [360,390,1280,1440]){
  await page.setViewportSize({width,height:900});await page.goto(origin+'/products');await page.getByRole('heading',{name:'在售商品',exact:true}).waitFor()
  for(const item of normal){const card=page.locator('.product-tile').filter({has:page.getByRole('heading',{name:item.goodsName,exact:true})});await card.waitFor();await card.locator('img').evaluate(i=>i.decode());if(!(await card.textContent()).includes(item.originalPrice))throw Error('List price changed')}
  if(await page.locator('.product-tile').count()!==6||!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))throw Error('Catalogue layout differs')
  const file='catalogue-final-'+width+'.png';await page.screenshot({path:path.join(work,file),fullPage:true});report.screenshots[file]=hash(path.join(work,file));report.checks.push('six-chinese-products-layout-'+width)
 }
 for(const item of normal){await page.goto(origin+'/products/'+item.goodsId);await page.getByRole('heading',{name:item.goodsName,exact:true}).waitFor();if(!(await page.locator('body').innerText()).includes(item.originalPrice))throw Error('Detail price changed');report.checks.push('anonymous-product-detail-'+item.key)}
 for(const id of targets){const r=await page.evaluate(async id=>{const r=await fetch('/api/v1/products/'+id);return{status:r.status,body:await r.json()}},id);if(r.status!==404)throw Error('Retired product still public');report.checks.push('retired-id-not-public-'+id)}
 await ctx.close()
 for(const key of ['b06buyer','b06buyer2']){
  const {ctx,page}=await context();let token
  page.on('response',async r=>{if(/\/auth\/(login|refresh)$/.test(r.url())&&r.status()===200)token=(await r.json()).data.accessToken})
  await page.goto(origin+'/login');await page.getByLabel('登录名').fill(accounts[key].loginName);await page.getByLabel('密码',{exact:true}).fill(accounts[key].password);await page.locator('form button[type=submit]').click();await page.getByRole('button',{name:'退出登录',exact:true}).waitFor()
  if(!await page.evaluate(()=>isSecureContext&&!!navigator.locks))throw Error('Untrusted browser context')
  const read=async route=>{const r=await page.evaluate(async({route,token})=>{const r=await fetch('/api/v1'+route,{headers:{Authorization:'Bearer '+token}});return{status:r.status,body:await r.json()}},{route,token});if(r.body.code!=='0000')throw Error('Historical read failed');return r.body.data}
  let original
  for(let pg=1;pg<100;pg++){const list=await read('/orders?page='+pg+'&size=20');original=list.items.find(x=>x.product.goodsId===targets[0]);if(original||pg*20>=list.total)break}
  if(!original)throw Error('No original seed order verified for buyer')
  const detail=await read('/orders/'+original.orderId);if(detail.product.goodsId!==targets[0]||detail.product.name!=='B06 demonstration product')throw Error('Historical snapshot changed')
  await page.goto(origin+'/orders/'+original.orderId);await page.getByRole('heading',{name:'订单详情',exact:true}).waitFor();report.originalOrders.push({orderId:original.orderId,status:detail.status,originalGoodsName:detail.product.name});await ctx.close()
 }
 if(report.pageErrors.length||report.blockedBusinessMutations)throw Error('Browser errors or business mutation attempt')
 report.status='PASS';save(path.join(work,'browser-report.json'),report);console.log('CAT02_BROWSER_PASS 6-normal/2-retired/original-order-snapshots-readable/GET-only-product-inspection')
}catch(e){report.status='FAIL';report.error=e.message;save(path.join(work,'browser-report.json'),report);throw e}finally{await browser.close()}
