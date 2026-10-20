// CAT05 real Edge acceptance. Writes only explicitly owned main sample goods.
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import { createHash } from 'node:crypto'
import { root, work, batch, origin, fixture as readFixture, Client, setSale, save as saveJson } from './cat05-lib.mjs'
const fixture=readFixture(),url=new URL(origin),target='main'
const {accounts}=await import('./cat05-lib.mjs')
const admin=new Client();await admin.login()
const write=(name,value)=>saveJson(path.join(work,name),value)
for(const id of Object.values(fixture.goods)){const item=fixture.items.find(x=>x.goodsId===id);if(!item||item.purpose!=='ACCEPTANCE')throw Error('Real trade is not owned ACCEPTANCE sample')}
  const { chromium }=createRequire(path.join(root,'frontend/package.json'))('playwright-core')
  const reportFile=path.join(work,'browser-report.json')
  const previous=fs.existsSync(reportFile)?JSON.parse(fs.readFileSync(reportFile)):null
  if(previous?.status==='PASSED'||fs.existsSync(path.join(work,'evidence-lock.json')))throw Error('Passed or evidenced batch is immutable')
if(previous)fs.copyFileSync(reportFile,path.join(work,'browser-report-before-resume-'+Date.now()+'.json'))
  fs.copyFileSync(import.meta.filename,path.join(work,'executed-browser.mjs'))
  const report={stage:'CAT-01.5',target,status:'RUNNING',httpsBypass:false,browserScriptSha256:createHash('sha256').update(fs.readFileSync(import.meta.filename)).digest('hex'),checks:[],orders:previous?.orders??{},confirmations:previous?.confirmations??{},writeJournal:previous?.writeJournal??[],paymentOwners:previous?.paymentOwners??{},pageErrors:[],resumed:!!previous}
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
    await ctx.route(origin+'/api/v1/**',async route=>{
     try{
      const req=route.request(),pathname=new URL(req.url()).pathname.slice('/api/v1'.length),method=req.method()
      if(!['POST','PUT','PATCH','DELETE'].includes(method)||pathname.startsWith('/auth/'))return route.continue()
      const body=req.postDataJSON(),owned=new Set(fixture.items.filter(x=>x.purpose==='ACCEPTANCE').map(x=>x.goodsId)),trial=pathname.match(/^\/products\/([^/]+)\/trial$/)
      if(method==='POST'&&trial&&(owned.has(trial[1])||fixture.showcase.some(x=>x.goodsId===trial[1])))return route.continue()
      const order=pathname.match(/^\/orders\/([^/]+)\/(payment-attempts|cancel)$/),payment=pathname.match(/^\/payments\/([^/]+)\/attempts\/([^/]+)\/simulated-results$/)
      const confirmation=pathname==='/purchase-confirmations'&&owned.has(body?.goodsId),purchase=pathname==='/orders'&&owned.has(report.confirmations[body?.confirmationId]?.body.goodsId)
      if(method!=='POST'||!(confirmation||purchase||order&&report.orders[order[1]]&&owned.has(report.orders[order[1]].goods)||payment&&report.paymentOwners[payment[1]]&&report.orders[report.paymentOwners[payment[1]]])){
        report.guardRejection={path:pathname,method};save();await route.abort('blockedbyclient');return
      }
      const op=body.operationId??body.purchaseIntentId
      const old=op&&report.writeJournal.find(x=>x.operationId===op)
      if(old&&(old.path!==pathname||JSON.stringify(old.body)!==JSON.stringify(body)))throw Error('Original operation body changed')
      const entry=old??{path:pathname,body,operationId:op??null,person:key,at:new Date().toISOString()}
      if(!old)report.writeJournal.push(entry);save()
      // Keep transport in Edge: its trusted CA and loopback resolver remain in force.
      await route.continue();const response=await req.response()
      if(!response){entry.response={status:'UNKNOWN'};save();return}
      const envelope=await response.json()
      entry.response={status:response.status(),code:envelope.code}
      if(envelope.code==='0000'&&confirmation){report.confirmations[envelope.data.confirmationId]={body,person:key};entry.confirmationId=envelope.data.confirmationId}
      if(envelope.code==='0000'&&purchase){const cf=report.confirmations[body.confirmationId],item=fixture.items.find(x=>x.goodsId===cf.body.goodsId);report.orders[envelope.data.orderId]={goods:item.goodsId,kind:item.key,teamId:envelope.data.teamId,mode:cf.body.mode};entry.orderId=envelope.data.orderId}
      if(envelope.code==='0000'&&order&&envelope.data?.paymentId)report.paymentOwners[envelope.data.paymentId]=order[1]
      save()
     }catch{
      report.transportOutcomeUnknown=true;save();await route.abort('failed').catch(()=>{})
     }
    })
    const page=await ctx.newPage();let token
    page.on('pageerror',e=>report.pageErrors.push(e.message))
    page.on('response',async r=>{
      if(/\/auth\/(login|refresh)$/.test(r.url())&&r.status()===200)token=(await r.json()).data.accessToken
      const match=new URL(r.url()).pathname.match(/^\/api\/v1\/orders\/([^/]+)\/payment$/)
      if(match&&report.orders[match[1]]&&r.status()===200){const p=(await r.json()).data?.payment;if(p){report.paymentOwners[p.paymentId]=match[1];save()}}
    })
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
  async function visualChecks(p) {
    let showcaseWrites=0
    const watch=r=>{if(r.method()==='POST'&&new URL(r.url()).pathname==='/api/v1/orders')showcaseWrites++}
    p.page.on('request',watch)
    for(const width of [360,390,1280,1440]) {
      await p.page.setViewportSize({width,height:900})
      await p.page.goto(origin+'/products');await p.page.getByRole('heading',{name:'在售商品',exact:true}).waitFor()
      for(const item of fixture.showcase) {
        const card=p.page.locator('.product-tile').filter({has:p.page.getByRole('heading',{name:item.fields.goodsName,exact:true})})
        await card.waitFor();await card.locator('img').evaluate(img=>img.decode())
        check(await card.locator('img').evaluate(i=>i.naturalWidth>0),'showcase-image-'+item.key+'-'+width)
      }
      await p.page.screenshot({path:path.join(work,'showcase-'+width+'.png'),fullPage:true})
      check(await p.page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'showcase-no-overflow-'+width)
    }
    for(const key of ['stockout','noactivity','badimage']) {
      const item=fixture.items.find(x=>x.key===key);await p.page.goto(origin+'/products/'+item.goodsId)
      await p.page.getByRole('heading',{name:item.fields.goodsName,exact:true}).waitFor()
      if(key==='badimage'){await p.page.locator('.image-placeholder').first().waitFor();check(true,'missing-image-placeholder')}
      else {await pause(1800);const button=p.page.getByRole('button',{name:'单独开团',exact:true});check(!await button.isVisible()||!await button.isEnabled(),key+'-no-purchase-button')}
      await p.page.screenshot({path:path.join(work,key+'-state.png'),fullPage:true})
    }
    for(const item of fixture.showcase) {
      await p.page.goto(origin+'/products/'+item.goodsId)
      await p.page.getByRole('heading',{name:item.fields.goodsName,exact:true}).waitFor()
      await p.page.getByRole('button',{name:'单独开团',exact:true}).waitFor({timeout:60000})
      check((await p.read('/products/'+item.goodsId)).syncReady,'showcase-read-only-ready-'+item.key)
    }
    p.page.off('request',watch);check(showcaseWrites===0,'showcase-no-order-writes')
    await p.page.setViewportSize({width:1280,height:900})
  }
  try {
    const buyer=await person('b06buyer'), other=await person('b06buyer2'), operator=await person('b06operator')
    check((await buyer.ctx.cookies()).some(c=>c.secure&&c.httpOnly),'secure-http-only-session-cookie')
    await visualChecks(buyer)
    const a=await purchase(buyer,'success')
    const hidden=await other.read('/products/'+fixture.goods.success+'/joinable-teams?limit=3');check(!JSON.stringify(hidden).includes(a.teamId),'unpaid-team-not-discoverable')
    await pay(buyer,a,true);const b=await purchase(other,'success',a.teamId);await pay(other,b)
    for(const [p,o]of[[buyer,a],[other,b]]){report.orders[o.orderId].final=await until(()=>p.read('/orders/'+o.orderId),x=>x.status==='GROUP_COMPLETED'&&x.fulfillmentSummary?.status==='PENDING','group complete');save();await readonly(p,'/orders/'+o.orderId,'成团成功，待履约','completed-'+o.orderId)}
    const e=await purchase(buyer,'expiry');await pay(buyer,e)
    const off=await purchase(other,'offpaid');await setSale(admin,'offpaid','OFF_SALE');await pay(other,off)
    check((await other.read('/orders/'+off.orderId)).product.name.includes('offpaid'),'off-sale-original-order-snapshot-readable')
    const c=await purchase(other,'cancel');await setSale(admin,'cancel','OFF_SALE');await readonly(other,'/orders/'+c.orderId,'取消未付款订单','unpaid-original-order')
    await other.page.getByRole('button',{name:'取消未付款订单',exact:true}).click();await other.page.getByRole('button',{name:'确认申请关闭',exact:true}).click()
    report.orders[c.orderId].final=await until(()=>other.read('/orders/'+c.orderId),x=>x.status==='CLOSED','unpaid cancellation');save()
    const forbidden=await other.page.evaluate(async({id,token})=>(await fetch('/api/v1/orders/'+id,{headers:{Authorization:'Bearer '+token}})).status,{id:a.orderId,token:other.token()});check(forbidden===404,'other-buyer-order-hidden')
    check(await buyer.page.evaluate(async token=>(await fetch('/api/v1/admin/refunds',{headers:{Authorization:'Bearer '+token}})).status,buyer.token())===403,'buyer-operator-api-forbidden')
    report.orders[e.orderId].final=await until(()=>buyer.read('/orders/'+e.orderId),x=>x.status==='CLOSED'&&x.refundSummary?.fundsStatus==='SUCCEEDED'&&x.refundSummary?.syncStatus==='ACCEPTED'&&x.refundSummary?.releaseStatus==='RELEASED','natural expiry full refund',300);save()
    await readonly(buyer,'/orders/'+e.orderId,'已全额退款，订单已关闭','natural-expiry-refund')
    report.orders[off.orderId].final=await until(()=>other.read('/orders/'+off.orderId),x=>x.status==='CLOSED'&&x.refundSummary?.fundsStatus==='SUCCEEDED'&&x.refundSummary?.syncStatus==='ACCEPTED'&&x.refundSummary?.releaseStatus==='RELEASED','off-sale-original-payment-and-natural-full-refund',300);save()
    await readonly(other,'/orders/'+off.orderId,'已全额退款，订单已关闭','off-sale-original-refund')
    await buyer.page.setViewportSize({width:390,height:844});await buyer.page.screenshot({path:path.join(work,'refund-mobile.png'),fullPage:true});check(await buyer.page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'mobile-no-overflow')
    await operator.page.goto(origin+'/admin/refunds/'+report.orders[e.orderId].final.refundSummary.refundId);await operator.page.screenshot({path:path.join(work,'operator-refund.png'),fullPage:true})
    check(report.pageErrors.length===0,'browser-no-page-errors');report.status='PASSED'
  } catch(e) {report.status='FAILED';report.error=e.message;for(let i=0;i<contexts.length;i++){const p=contexts[i].pages()[0];await p.screenshot({path:path.join(work,'failure-'+i+'.png'),fullPage:true}).catch(()=>{});fs.writeFileSync(path.join(work,'failure-'+i+'.txt'),await p.locator('body').innerText().catch(()=>''))}throw e}
  finally {save();for(let i=0;i<contexts.length;i++)await contexts[i].storageState({path:path.join(work,'session-'+i+'.json')});await browser.close()}
