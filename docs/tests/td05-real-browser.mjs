import {createRequire} from 'node:module';
import fs from 'node:fs';import path from 'node:path';import https from 'node:https';import {randomUUID,createHash} from 'node:crypto';
const root=path.resolve(import.meta.dirname,'../..'), work=process.env.B06_BROWSER_WORK??path.join(root,'.local/b06/browser',process.argv[3]??'');
const mode=process.argv[2],origin='https://zj-market.test:8445';
const accounts=JSON.parse(fs.readFileSync(path.join(process.env.B06_BROWSER_CONTROL??path.join(root,'.local/b06/control'),'demo-accounts.json')));
const ca=fs.readFileSync(path.join(process.env.B06_BROWSER_RUNTIME??path.join(root,'.local/b06/runtime'),'web-ca.pem'));
const require=createRequire(path.join(root,'frontend/package.json'));
const {chromium}=require('playwright-core');
const report={stage:process.env.B06_BROWSER_STAGE??'B-06.3',status:'RUNNING',checks:[],orders:{},pageErrors:[],httpsBypass:false,browserScriptSha256:createHash('sha256').update(fs.readFileSync(import.meta.filename)).digest('hex')};
const check=(ok,name)=>{if(!ok)throw Error(name);report.checks.push(name);console.log('PASS '+name)};
const pause=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn,predicate,name,seconds=100){const deadline=Date.now()+seconds*1000;let value;do{value=await fn();if(predicate(value))return value;await pause(1500)}while(Date.now()<deadline);throw Error('Timeout '+name+'; last='+JSON.stringify(value))}
let access;const cookies=new Map();
function direct(route,method='GET',body,extra={}){return new Promise((resolve,reject)=>{const req=https.request({hostname:'zj-market.test',port:8445,path:'/api/v1'+route,method,ca,rejectUnauthorized:true,family:4,autoSelectFamily:false,lookup:(_h,_o,cb)=>cb(null,'127.0.0.1',4),headers:{Origin:origin,'Content-Type':'application/json',Cookie:[...cookies].map(([k,v])=>k+'='+v).join('; '),...(access?{Authorization:'Bearer '+access}:{}),...extra}},res=>{for(const c of res.headers['set-cookie']??[]){const s=c.split(';')[0],i=s.indexOf('=');cookies.set(s.slice(0,i),s.slice(i+1))}let text='';res.on('data',b=>text+=b);res.on('end',()=>resolve({status:res.statusCode,...JSON.parse(text)}))});req.on('error',reject);req.setTimeout(15000,()=>req.destroy(Error('HTTPS timeout')));if(body!==undefined)req.write(JSON.stringify(body));req.end()})}
async function api(route,method='GET',body,extra){const r=await direct(route,method,body,extra);if(r.code!=='0000')throw Error(route+' '+r.status+' '+r.code);return r.data}
if(mode==='prepare'){
 fs.mkdirSync(work,{recursive:false});
 const csrf=await api('/auth/csrf');const auth=await api('/auth/login','POST',accounts.b06operator,{[csrf.headerName]:csrf.token});access=auth.accessToken;
 const fixture={batch:path.basename(work),goods:{}};
 for(const name of ['success','expiry','cancel']){
  const product=await api('/admin/products','POST',{goodsName:'TD05 '+path.basename(work)+' '+name,description:'Independent normal-flow acceptance',imageUrl:null,originalPrice:'100.00',currency:'CNY',saleStatus:'ON_SALE'});
  fixture.goods[name]=product.goodsId;fs.writeFileSync(path.join(work,'fixture.json'),JSON.stringify(fixture,null,2));
  const inv=await api('/admin/inventory/'+product.goodsId);
  await api('/admin/inventory/'+product.goodsId+'/inbounds','POST',{operationId:randomUUID(),quantity:'10',expectedVersion:inv.version,reason:'TD05 independent batch initial stock'});
 }
 fs.writeFileSync(path.join(work,'fixture.json'),JSON.stringify(fixture,null,2));console.log('PREPARE_PASS');
}else if(mode==='browser'){
 const fixture=JSON.parse(fs.readFileSync(path.join(work,'fixture.json')));
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',args:['--host-resolver-rules=MAP zj-market.test 127.0.0.1','--no-proxy-server']});
 const contexts=[];report.paymentResponses=[];
 async function person(account){const ctx=await browser.newContext({viewport:{width:1280,height:900},ignoreHTTPSErrors:false});contexts.push(ctx);const page=await ctx.newPage();let token;
 page.on('pageerror',e=>report.pageErrors.push(e.message));page.on('response',async r=>{if(/\/(?:payment-attempts|simulated-results)$/.test(r.url())){const b=await r.json();report.paymentResponses.push({path:new URL(r.url()).pathname,status:r.status(),code:b.code,operationId:b.data?.operationId??null})}});page.on('response',async r=>{if(/\/auth\/(login|refresh)$/.test(r.url())&&r.status()===200){const b=await r.json();token=b.data.accessToken}});
 await page.goto(origin+'/login');check(await page.evaluate(()=>isSecureContext&&!!navigator.locks),'trusted-https-web-locks-'+account);
 await page.getByLabel('登录名').fill(accounts[account].loginName);await page.getByLabel('密码',{exact:true}).fill(accounts[account].password);await page.locator('form button[type=submit]').click();await page.getByRole('button',{name:'退出登录',exact:true}).waitFor();
 const read=async(route)=>{const r=await page.evaluate(async({route,token})=>{const r=await fetch('/api/v1'+route,{headers:{Authorization:'Bearer '+token},cache:'no-store'});return {status:r.status,body:await r.json()}},{route,token});if(r.body.code!=='0000')throw Error('Read '+route+' '+r.status+' '+r.body.code);return r.body.data};
 return {page,ctx,read,getToken:()=>token};}
 async function purchase(p,goods,team){
  if(team){
   await p.page.goto(origin+'/products/'+goods);
   const selected=p.page.locator('.joinable-card').filter({has:p.page.locator('a[href="/teams/'+encodeURIComponent(team)+'"]')});
   await selected.getByRole('link',{name:'去参团',exact:true}).waitFor({timeout:100000});
   await selected.getByRole('link',{name:'去参团',exact:true}).click();
   check(p.page.url()===origin+'/teams/'+encodeURIComponent(team),'discover-exact-team-from-product');
  }else{
   await p.page.goto(origin+'/');await p.page.getByRole('heading',{name:'在售商品',exact:true}).waitFor();
   await until(()=>p.page.getByRole('button',{name:'刷新列表',exact:true}).isEnabled(),Boolean,'homepage catalogue loaded');
   const kind=Object.entries(fixture.goods).find(([,id])=>id===goods)?.[0];const name='TD05 '+fixture.batch+' '+kind;
   const card=p.page.locator('.product-tile').filter({hasText:name});let pageNo=1;
   while(!await card.count()){
    if(pageNo>=10)throw Error('Catalogue product not found');const next=p.page.getByRole('button',{name:'下一页',exact:true});if(!await next.isEnabled())throw Error('Catalogue product missing');await next.click();pageNo++;
    await p.page.locator('.pagination').getByText(new RegExp('第 '+pageNo+' 页')).waitFor();
   }
   if(kind==='success')await p.page.screenshot({path:path.join(work,'homepage-selection.png'),fullPage:true});
   await card.getByRole('button',{name:'查看详情',exact:true}).click();
   check(p.page.url()===origin+'/products/'+goods,'homepage-select-'+kind);
  }
  const quote=p.page.getByRole('button',{name:team?'核对参团报价':'核对开团报价',exact:true});
  const purchase=p.page.locator('section[aria-label="购买确认"]');
  const link=purchase.getByRole('link',{name:'查看原订单',exact:true});
  const active=await p.read('/products/'+goods+'/active-order');
  const state=active?'existing':await until(async()=>{if(await link.isVisible().catch(()=>false))return 'existing';if(await quote.isEnabled().catch(()=>false))return 'new';if(!team){const retry=p.page.getByRole('button',{name:'重新试算',exact:true});if(await retry.isEnabled().catch(()=>false))await retry.click()}return null},Boolean,'quote or original order ready');
  if(state==='new'){
   await quote.click();await p.page.getByRole('button',{name:'确认购买',exact:true}).click();
  }
  await link.waitFor();const id=(await link.getAttribute('href')).split('/')[2];
  const o=await until(()=>p.read('/orders/'+id),x=>x.status==='WAITING_PAYMENT','actual A reservation');report.orders[id]={goods,teamId:o.teamId,mode:o.mode};return o;
 }
 async function selectReady(p){await until(async()=>{const choose=p.page.getByRole('button',{name:'选择模拟成功',exact:true});if(await choose.isVisible()&&await choose.isEnabled())return true;const retry=p.page.getByRole('button',{name:'重试原操作',exact:true});if(await retry.isVisible()&&await retry.isEnabled()){await retry.click();}return false},Boolean,'original payment operation ready',60)}
 async function pay(p,o,failedFirst=false){await p.page.goto(origin+'/orders/'+o.orderId+'/payment');await p.page.getByRole('button',{name:'创建模拟支付尝试',exact:true}).click();await selectReady(p);
  let before;if(failedFirst){before=await p.read('/orders/'+o.orderId+'/payment');await p.page.getByRole('button',{name:'选择模拟失败',exact:true}).click();await p.page.getByRole('button',{name:'重新尝试模拟支付',exact:true}).click();await selectReady(p);const after=await p.read('/orders/'+o.orderId+'/payment');check(before.payment.paymentId===after.payment.paymentId&&after.payment.attempts.length===2&&after.payment.attempts.some(a=>a.state==='FAILED'),'stable-payment-root-failed-attempt-retry')}
  await p.page.getByRole('button',{name:'选择模拟成功',exact:true}).click();const paid=await until(()=>p.read('/orders/'+o.orderId+'/payment'),x=>x.payment?.fundsState==='SUCCEEDED'&&x.payment.aAcceptance==='ACCEPTED','actual payment and A acceptance');check(paid.payment.amount==='90.00','trusted-simulated-amount-'+o.orderId);
 }
 async function readonly(p,url,text,screenshot){await p.page.goto(origin+url);await p.page.getByText(text,{exact:false}).first().waitFor({timeout:100000});let writes=0;const capture=r=>{if(['POST','PUT','PATCH','DELETE'].includes(r.method())&&r.url().startsWith(origin+'/api/')&&!r.url().includes('/auth/'))writes++};p.page.on('request',capture);await p.page.reload();await p.page.getByText(text,{exact:false}).first().waitFor();await p.page.screenshot({path:path.join(work,screenshot+'.png'),fullPage:true});p.page.off('request',capture);check(writes===0,'reload-no-business-writes-'+screenshot)}
 try{
  const buyer=await person('b06buyer'),other=await person('b06buyer2'),operator=await person('b06operator');
  const cs=await buyer.ctx.cookies();check(cs.some(c=>c.secure&&c.httpOnly),'secure-http-only-refresh-cookie');
  let refresh=0;buyer.page.on('response',r=>{if(r.url().endsWith('/auth/refresh')&&r.status()===200)refresh++});await buyer.page.reload();await buyer.page.getByRole('button',{name:'退出登录',exact:true}).waitFor();check(refresh>0,'real-page-reload-session-refresh');
  const a=await purchase(buyer,fixture.goods.success);await pay(buyer,a,true);const b=await purchase(other,fixture.goods.success,a.teamId);await pay(other,b);
  for(const [p,o] of [[buyer,a],[other,b]]){const final=await until(()=>p.read('/orders/'+o.orderId),x=>x.status==='GROUP_COMPLETED'&&x.fulfillmentSummary?.status==='PENDING','group completion');report.orders[o.orderId].final=final;await readonly(p,'/orders/'+o.orderId,'成团成功，库存已确认，等待履约。','completed-'+o.orderId)}
  check(a.teamId===b.teamId&&b.mode==='JOIN','actual-open-join-one-team');
  const e=await purchase(buyer,fixture.goods.expiry);await pay(buyer,e);const expiryPaid=await buyer.read('/orders/'+e.orderId);check(expiryPaid.status!=='GROUP_COMPLETED','partial-team-waits-natural-expiry');
  const c=await purchase(other,fixture.goods.cancel);await other.page.goto(origin+'/orders/'+c.orderId);await other.page.getByRole('button',{name:'申请关闭订单',exact:true}).click();const cancelled=await until(()=>other.read('/orders/'+c.orderId),x=>x.status==='CLOSED','unpaid cancellation');report.orders[c.orderId].final=cancelled;await readonly(other,'/orders/'+c.orderId,'库存已释放','unpaid-cancelled');
  const forbidden=await other.page.evaluate(async({id,token})=>{const r=await fetch('/api/v1/orders/'+id,{headers:{Authorization:'Bearer '+token}});return r.status},{id:a.orderId,token:other.getToken()});check(forbidden===404,'other-buyer-order-hidden');
  const adminForbidden=await buyer.page.evaluate(async token=>{const r=await fetch('/api/v1/admin/refunds',{headers:{Authorization:'Bearer '+token}});return r.status},buyer.getToken());check(adminForbidden===403,'buyer-cannot-read-operator-api');
  const wrongOrigin=await direct('/auth/refresh','POST',{}, {Origin:'https://evil.invalid'});check(wrongOrigin.status===403,'foreign-origin-rejected');
  const ended=await until(()=>buyer.read('/orders/'+e.orderId),x=>x.status==='CLOSED'&&x.refundSummary?.fundsStatus==='SUCCEEDED'&&x.refundSummary?.syncStatus==='ACCEPTED'&&x.refundSummary?.releaseStatus==='RELEASED','natural expiry refund sync release',240);report.orders[e.orderId].final=ended;
  await readonly(buyer,'/orders/'+e.orderId,'已全额退款','natural-expiry-refund');
  await buyer.page.setViewportSize({width:390,height:844});await buyer.page.screenshot({path:path.join(work,'refund-mobile.png'),fullPage:true});check(await buyer.page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'buyer-mobile-no-overflow');
  const refund=await buyer.read('/orders/'+e.orderId+'/refund');fs.writeFileSync(path.join(work,'refund.json'),JSON.stringify(refund,null,2));
  await readonly(operator,'/admin/refunds/'+ended.refundSummary.refundId,'退款 '+ended.refundSummary.refundId,'operator-refund');
  await operator.page.goto(origin+'/admin/reconciliations');await operator.page.getByRole('heading',{name:'团队完整核对',exact:true}).waitFor();await operator.page.screenshot({path:path.join(work,'operator-reconciliations.png'),fullPage:true});
  await operator.page.goto(origin+'/admin/inventory');await operator.page.getByRole('heading',{name:'库存管理',exact:true}).waitFor();await operator.page.screenshot({path:path.join(work,'operator-stock.png'),fullPage:true});
  check(report.pageErrors.length===0,'browser-no-page-errors');report.status='PASSED';
 }catch(e){report.status='FAILED';report.error=e.message;for(let i=0;i<contexts.length;i++){const p=contexts[i].pages()[0];if(p){await p.screenshot({path:path.join(work,'failure-'+i+'.png'),fullPage:true}).catch(()=>{});fs.writeFileSync(path.join(work,'failure-'+i+'.txt'),await p.locator('body').innerText().catch(()=>''))}}throw e}
 finally{fs.writeFileSync(path.join(work,'browser-report.json'),JSON.stringify(report,null,2));await browser.close()}
}else throw Error('Mode required');

