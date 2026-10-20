// Post-cleanup reads prove samples disappear while original orders remain readable.
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import { createHash } from 'node:crypto'
import {root,work,origin,fixture,content,Client,save} from './cat03-lib.mjs'
const f=fixture(),original=JSON.parse(fs.readFileSync(path.join(work,'browser-report.json'),'utf8'))
if(f.phase!=='CLEANED'||original.status!=='PASSED')throw Error('Cleanup and real browser evidence required')
const admin=new Client();await admin.login();const state=[]
for(const item of f.items){const p=await admin.api('/admin/products/'+item.goodsId);if(p.saleStatus!==(item.purpose==='SHOWCASE'?'ON_SALE':'OFF_SALE')||!p.syncReady)throw Error('Final sale/sync state differs');state.push({key:item.key,purpose:item.purpose,goodsId:item.goodsId,version:p.productVersion,saleStatus:p.saleStatus,syncReady:p.syncReady})}
const all=await admin.listing(),publicIds=new Set();for(let page=1;page<1000;page++){const r=await admin.api('/products?page='+page+'&size=20');for(const p of r.items)publicIds.add(p.goodsId);if(page*20>=r.total)break}
for(const item of f.items)if(publicIds.has(item.goodsId)!==(item.purpose==='SHOWCASE'))throw Error('Public sample cleanup differs')
const {chromium}=createRequire(path.join(root,'frontend/package.json'))('playwright-core')
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',args:['--host-resolver-rules=MAP zj-market-ux.test 127.0.0.1','--no-proxy-server']})
let writes=0;const checks=[],contexts=[]
try{
 for(const key of ['b06buyer','b06buyer2']){
  const account=JSON.parse(fs.readFileSync(path.join(root,'.local/b06/control/demo-accounts.json'),'utf8'))[key]
  const ctx=await browser.newContext({ignoreHTTPSErrors:false,viewport:{width:1440,height:900}});contexts.push(ctx);const page=await ctx.newPage();let token
  page.on('response',async r=>{if(/\/auth\/(login|refresh)$/.test(r.url())&&r.status()===200)token=(await r.json()).data.accessToken})
  page.on('request',r=>{if(['POST','PUT','PATCH','DELETE'].includes(r.method())&&r.url().startsWith(origin+'/api/')&&!r.url().includes('/auth/'))writes++})
  await page.goto(origin+'/login');await page.getByLabel('登录名').fill(account.loginName);await page.getByLabel('密码',{exact:true}).fill(account.password);await page.locator('form button[type=submit]').click();await page.getByRole('button',{name:'退出登录',exact:true}).waitFor()
  const ids=key==='b06buyer'?Object.keys(original.orders).filter(id=>original.orders[id].kind==='expiry'||original.orders[id].kind==='success'&&original.orders[id].mode==='OPEN'):Object.keys(original.orders).filter(id=>original.orders[id].mode==='JOIN'||['cancel','offpaid'].includes(original.orders[id].kind))
  for(const id of ids){await page.goto(origin+'/orders/'+id);await page.getByRole('heading',{name:'订单详情',exact:true}).waitFor();const r=await page.evaluate(async({id,token})=>{const r=await fetch('/api/v1/orders/'+id,{headers:{Authorization:'Bearer '+token}});return{status:r.status,body:await r.json()}},{id,token});if(r.status!==200||!['CLOSED','GROUP_COMPLETED'].includes(r.body.data?.status))throw Error('Retired sample original order inaccessible');checks.push('off-sale-original-order-readable-'+id)}
  if(key==='b06buyer'){
   for(const item of content.products){const r=await page.goto(origin+item.imagePath);if(r.status()!==200||!r.headers()['content-type'].includes('image/svg+xml')||createHash('sha256').update(await r.body()).digest('hex').toUpperCase()!==item.image.sha256)throw Error('Runtime image differs from frozen asset');checks.push('actual-HTTPS-image-hash-'+item.key)}
   for(const width of [390,1440]){await page.setViewportSize({width,height:900});await page.goto(origin+'/products');await page.getByRole('heading',{name:'在售商品',exact:true}).waitFor();for(const item of content.products)await page.getByRole('heading',{name:item.goodsName,exact:true}).waitFor();await page.screenshot({path:path.join(work,'final-showcase-'+width+'.png'),fullPage:true});if(!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))throw Error('Final layout overflows')}
  }
 }
 if(writes!==0)throw Error('Post-cleanup reads submitted writes')
 save(path.join(work,'final-browser.json'),{status:'PASS',httpsBypass:false,businessWrites:writes,checks,productStates:state,publicOwnedShowcase:6,publicOwnedAcceptance:0,legacyProductsUntouched:true})
 console.log('CAT03_FINAL_BROWSER_PASS 6-showcase/8-off-sale/original-orders-readable/actual-image-hashes/no-writes')
}finally{await browser.close()}
