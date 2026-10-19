// Release acceptance uses real HTTPS and normal UI writes; fixtures retain original keys.
import fs from 'node:fs'
import path from 'node:path'
import https from 'node:https'
import { createRequire } from 'node:module'
import { randomUUID, createHash } from 'node:crypto'
const root = path.resolve(import.meta.dirname, '..'), [mode, target, batch] = process.argv.slice(2)
if (!['prepare', 'browser'].includes(mode) || !['ux', 'main'].includes(target) || !/^ux05-[0-9]{8}-[0-9]{2}$/.test(batch)) throw Error('Explicit owned batch and target required')
const work = path.join(root, '.local/ux05', batch + '-' + target)
fs.mkdirSync(work, { recursive: true })
const origin = target === 'ux' ? 'https://zj-market-ux.test:8446' : 'https://zj-market.test'
let accountFile, caFile
if (target === 'ux') {
  accountFile = path.join(root, '.local/b06/control/demo-accounts.json'); caFile = path.join(root, '.local/b06/runtime/web-ca.pem')
} else {
  const privateRoot = 'D:/Java/zj-market-stable/private', manifest = JSON.parse(fs.readFileSync(privateRoot + '/files-manifest.json'))
  accountFile = path.join(privateRoot, manifest.probe['demo-accounts.json'].relativePath); caFile = path.join(privateRoot, manifest.probe['web-ca.pem'].relativePath)
}
const accounts = JSON.parse(fs.readFileSync(accountFile)), ca = fs.readFileSync(caFile), url = new URL(origin)
let access; const cookies = new Map()
function direct(route, method = 'GET', body, extra = {}) {
  return new Promise((resolve, reject) => {
    const req = https.request({ hostname: url.hostname, port: url.port || 443, path: '/api/v1' + route, method, ca, rejectUnauthorized: true,
      family: 4, autoSelectFamily: false, lookup: (_h, _o, cb) => cb(null, '127.0.0.1', 4),
      headers: { Origin: origin, 'Content-Type': 'application/json', Cookie: [...cookies].map(([k,v]) => k+'='+v).join('; '), ...(access ? { Authorization: 'Bearer '+access } : {}), ...extra } }, res => {
      for (const c of res.headers['set-cookie'] ?? []) { const s=c.split(';')[0], i=s.indexOf('='); cookies.set(s.slice(0,i),s.slice(i+1)) }
      let text=''; res.on('data',b=>text+=b); res.on('end',()=>{try { resolve({status:res.statusCode,...JSON.parse(text)}) } catch { reject(Error('Invalid API response; original operation retained')) }})
    })
    req.on('error',()=>reject(Error('API outcome unknown; original operation retained'))); req.setTimeout(15000,()=>req.destroy())
    if (body !== undefined) req.write(JSON.stringify(body)); req.end()
  })
}
async function api(route,method='GET',body,extra) { const r=await direct(route,method,body,extra); if(r.code!=='0000') throw Error(route+' '+r.status+' '+r.code); return r.data }
const write=(file,value)=>fs.writeFileSync(path.join(work,file),JSON.stringify(value,null,2)+'\n')
const fixtureFile=path.join(work,'fixture.json')
let fixture=fs.existsSync(fixtureFile)?JSON.parse(fs.readFileSync(fixtureFile)):{batch,target,origin,goods:{},items:{}}
if(fixture.target!==target||fixture.origin!==origin)throw Error('Fixture ownership mismatch')
if(mode==='prepare') {
  const csrf=await api('/auth/csrf'), a=accounts.b06operator
  access=(await api('/auth/login','POST',{loginName:a.loginName,password:a.password},{[csrf.headerName]:csrf.token})).accessToken
  for(const kind of ['success','expiry','cancel']) {
    const item=fixture.items[kind]??={name:'UX05 '+batch+' '+kind}
    if(!fixture.goods[kind]) {
      if(item.createStarted)throw Error('Unknown product creation; reconcile original product before continuing')
      item.createStarted=true;write('fixture.json',fixture)
      const product=await api('/admin/products','POST',{goodsName:item.name,description:'UX-05 本机验收样本，模拟资金，不发货',imageUrl:origin+'/demo/ux04-cup.svg',originalPrice:'100.00',currency:'CNY',saleStatus:'ON_SALE'})
      fixture.goods[kind]=product.goodsId;write('fixture.json',fixture)
    }
    const goods=fixture.goods[kind]
    if(!item.stockRequest) { const inv=await api('/admin/inventory/'+goods);item.stockRequest={operationId:randomUUID(),quantity:'10',expectedVersion:inv.version,reason:'UX05 owned acceptance initial stock'};write('fixture.json',fixture) }
    const previous=await direct('/admin/inventory/operations/'+item.stockRequest.operationId)
    const op=previous.status===404?await api('/admin/inventory/'+goods+'/inbounds','POST',item.stockRequest):previous.data
    if(op?.outcome!=='SUCCEEDED'||op.operationId!==item.stockRequest.operationId)throw Error('Original stock operation not confirmed')
    item.stockConfirmed=true;write('fixture.json',fixture)
  }
  console.log('UX05_PREPARED '+target)
} else {
  const { chromium }=createRequire(path.join(root,'frontend/package.json'))('playwright-core')
  const reportFile=path.join(work,'browser-report.json')
  const previous=fs.existsSync(reportFile)?JSON.parse(fs.readFileSync(reportFile)):null
  if(previous?.status==='PASSED')throw Error('Passed batch is immutable')
  fs.copyFileSync(import.meta.filename,path.join(work,'executed-browser.mjs'))
  const report={stage:'UX-05',target,status:'RUNNING',httpsBypass:false,browserScriptSha256:createHash('sha256').update(fs.readFileSync(import.meta.filename)).digest('hex'),checks:[],orders:previous?.orders??{},pageErrors:[],resumed:!!previous}
  const save=()=>write('browser-report.json',report)
  const check=(ok,name)=>{if(!ok)throw Error(name);report.checks.push(name);save();console.log('PASS '+name)}
  const pause=ms=>new Promise(r=>setTimeout(r,ms))
  async function until(fn,predicate,name,seconds=120) { const deadline=Date.now()+seconds*1000;let value;do{value=await fn();if(predicate(value))return value;await pause(1200)}while(Date.now()<deadline);throw Error('Timeout '+name+'; last='+JSON.stringify(value)) }
  const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',args:['--host-resolver-rules=MAP '+url.hostname+' 127.0.0.1','--no-proxy-server']})
  const contexts=[]
  async function person(key) {
    const state=path.join(work,'session-'+contexts.length+'.json')
    const stored=fs.existsSync(state)?JSON.parse(fs.readFileSync(state)):null
    if(stored)stored.cookies=[] // Restore original operation keys; obtain a fresh identity through explicit login.
    const ctx=await browser.newContext({viewport:{width:1280,height:900},ignoreHTTPSErrors:false,...(stored?{storageState:stored}:{})});contexts.push(ctx)
    const page=await ctx.newPage();let token
    page.on('pageerror',e=>report.pageErrors.push(e.message))
    page.on('response',async r=>{if(/\/auth\/(login|refresh)$/.test(r.url())&&r.status()===200)token=(await r.json()).data.accessToken})
    await page.goto(origin+'/login');check(await page.evaluate(()=>isSecureContext&&!!navigator.locks),'trusted-HTTPS-'+key)
    await page.getByLabel('登录名').fill(accounts[key].loginName);await page.getByLabel('密码',{exact:true}).fill(accounts[key].password)
    await page.locator('form button[type=submit]').click();await page.getByRole('button',{name:'退出登录',exact:true}).waitFor()
    const read=async route=>{const r=await page.evaluate(async({route,token})=>{const r=await fetch('/api/v1'+route,{headers:{Authorization:'Bearer '+token},cache:'no-store'});return{status:r.status,body:await r.json()}},{route,token});if(r.body.code!=='0000')throw Error('Read '+route+' '+r.status+' '+r.body.code);return r.body.data}
    return {page,ctx,read,token:()=>token}
  }
  async function purchase(p,kind,team) {
    const original=Object.entries(report.orders).find(([,o])=>o.kind===kind&&(team?o.mode==='JOIN':o.mode==='OPEN'))
    if(original) {const o=await p.read('/orders/'+original[0]);check(o.teamId===original[1].teamId,'resume-original-order-'+kind);return o}
    const goods=fixture.goods[kind];await p.page.goto(origin+'/products/'+goods)
    if(team) { const card=p.page.locator('.joinable-card').filter({has:p.page.locator('a[href="/teams/'+team+'"]')});await card.getByRole('link',{name:'去参团',exact:true}).waitFor({timeout:100000});await card.getByRole('link',{name:'去参团',exact:true}).click();check(p.page.url()===origin+'/teams/'+team,'product-discovery-selected-exact-team') }
    await p.page.getByRole('button',{name:team?'加入此团队':'单独开团',exact:true}).click({timeout:100000})
    const response=p.page.waitForResponse(r=>new URL(r.url()).pathname==='/api/v1/orders'&&r.request().method()==='POST')
    await p.page.getByRole('button',{name:'确认下单并去支付',exact:true}).click()
    const res=await response, data=(await res.json()).data
    if(!data?.orderId)throw Error('Order response missing identity; retain browser pending intent')
    report.orders[data.orderId]={goods,kind,teamId:data.teamId,mode:data.mode};save()
    const order=await until(()=>p.read('/orders/'+data.orderId),x=>x.status==='WAITING_PAYMENT','actual A reservation')
    Object.assign(report.orders[order.orderId],{teamId:order.teamId,mode:order.mode});save()
    check((!team&&order.mode==='OPEN')||(team&&order.teamId===team&&order.mode==='JOIN'),'two-confirmations-one-order-'+kind)
    return order
  }
  async function pay(p,o,failedFirst=false) {
    await p.page.goto(origin+'/orders/'+o.orderId+'/payment')
    const initial=await p.read('/orders/'+o.orderId+'/payment')
    if(initial.payment?.fundsState==='SUCCEEDED') {check(initial.payment.aAcceptance==='ACCEPTED','resume-original-paid-order');return}
    async function choose(label) {
      const primary=p.page.getByRole('button',{name:label,exact:true})
      const recovering=await p.page.evaluate(id=>Object.keys(localStorage).some(k=>(k.startsWith('b-payment:')||k.startsWith('b-payment-flow:'))&&k.endsWith(':'+id)),o.orderId)
      if(!recovering)await primary.click({timeout:60000})
      await until(async()=>{
        const v=await p.read('/orders/'+o.orderId+'/payment')
        for(const name of ['用原编号重试','继续本次模拟支付']) {const button=p.page.getByRole('button',{name,exact:true});if(await button.isVisible().catch(()=>false)&&await button.isEnabled())await button.click()}
        return v
      },x=>label==='模拟本次支付失败'?x.payment?.attempts?.some(a=>a.attemptId===x.payment.activeAttemptId&&a.state==='FAILED'):x.payment?.fundsState==='SUCCEEDED','payment original operation')
    }
    if(failedFirst) {if(!initial.payment?.attempts?.some(a=>a.state==='FAILED'))await choose('模拟本次支付失败');const before=await p.read('/orders/'+o.orderId+'/payment');await p.page.getByRole('button',{name:'再次模拟支付成功',exact:true}).waitFor({timeout:60000});await choose('再次模拟支付成功');const after=await p.read('/orders/'+o.orderId+'/payment');check(before.payment.paymentId===after.payment.paymentId&&after.payment.attempts.length===2,'failed-attempt-retry-same-payment-root')}
    else await choose('模拟支付成功')
    const paid=await until(()=>p.read('/orders/'+o.orderId+'/payment'),x=>x.payment?.fundsState==='SUCCEEDED'&&x.payment.aAcceptance==='ACCEPTED','funds and A confirmation')
    check(paid.payment.amount==='90.00','actual-payment-90-'+o.orderId)
  }
  async function readonly(p,route,text,file) {
    await p.page.goto(origin+route);await p.page.getByText(text,{exact:false}).first().waitFor({timeout:100000})
    let writes=0;const capture=r=>{if(['POST','PUT','PATCH','DELETE'].includes(r.method())&&r.url().startsWith(origin+'/api/')&&!r.url().includes('/auth/'))writes++}
    p.page.on('request',capture);await p.page.reload();await p.page.getByText(text,{exact:false}).first().waitFor();await p.page.screenshot({path:path.join(work,file+'.png'),fullPage:true});p.page.off('request',capture);check(writes===0,'reload-no-business-writes-'+file)
  }
  try {
    const buyer=await person('b06buyer'), other=await person('b06buyer2'), operator=await person('b06operator')
    check((await buyer.ctx.cookies()).some(c=>c.secure&&c.httpOnly),'secure-http-only-session-cookie')
    const a=await purchase(buyer,'success')
    const hidden=await other.read('/products/'+fixture.goods.success+'/joinable-teams?limit=3');check(!JSON.stringify(hidden).includes(a.teamId),'unpaid-team-not-discoverable')
    await pay(buyer,a,true);const b=await purchase(other,'success',a.teamId);await pay(other,b)
    for(const [p,o]of[[buyer,a],[other,b]]){report.orders[o.orderId].final=await until(()=>p.read('/orders/'+o.orderId),x=>x.status==='GROUP_COMPLETED'&&x.fulfillmentSummary?.status==='PENDING','group complete');save();await readonly(p,'/orders/'+o.orderId,'成团成功，待履约','completed-'+o.orderId)}
    const e=await purchase(buyer,'expiry');await pay(buyer,e)
    const c=await purchase(other,'cancel');await readonly(other,'/orders/'+c.orderId,'取消未付款订单','unpaid-original-order')
    await other.page.getByRole('button',{name:'取消未付款订单',exact:true}).click();await other.page.getByRole('button',{name:'确认申请关闭',exact:true}).click()
    report.orders[c.orderId].final=await until(()=>other.read('/orders/'+c.orderId),x=>x.status==='CLOSED','unpaid cancellation');save()
    const forbidden=await other.page.evaluate(async({id,token})=>(await fetch('/api/v1/orders/'+id,{headers:{Authorization:'Bearer '+token}})).status,{id:a.orderId,token:other.token()});check(forbidden===404,'other-buyer-order-hidden')
    check(await buyer.page.evaluate(async token=>(await fetch('/api/v1/admin/refunds',{headers:{Authorization:'Bearer '+token}})).status,buyer.token())===403,'buyer-operator-api-forbidden')
    report.orders[e.orderId].final=await until(()=>buyer.read('/orders/'+e.orderId),x=>x.status==='CLOSED'&&x.refundSummary?.fundsStatus==='SUCCEEDED'&&x.refundSummary?.syncStatus==='ACCEPTED'&&x.refundSummary?.releaseStatus==='RELEASED','natural expiry full refund',300);save()
    await readonly(buyer,'/orders/'+e.orderId,'已全额退款，订单已关闭','natural-expiry-refund')
    await buyer.page.setViewportSize({width:390,height:844});await buyer.page.screenshot({path:path.join(work,'refund-mobile.png'),fullPage:true});check(await buyer.page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'mobile-no-overflow')
    await operator.page.goto(origin+'/admin/refunds/'+report.orders[e.orderId].final.refundSummary.refundId);await operator.page.screenshot({path:path.join(work,'operator-refund.png'),fullPage:true})
    check(report.pageErrors.length===0,'browser-no-page-errors');report.status='PASSED'
  } catch(e) {report.status='FAILED';report.error=e.message;for(let i=0;i<contexts.length;i++){const p=contexts[i].pages()[0];await p.screenshot({path:path.join(work,'failure-'+i+'.png'),fullPage:true}).catch(()=>{});fs.writeFileSync(path.join(work,'failure-'+i+'.txt'),await p.locator('body').innerText().catch(()=>''))}throw e}
  finally {save();for(let i=0;i<contexts.length;i++)await contexts[i].storageState({path:path.join(work,'session-'+i+'.json')});await browser.close()}
}
