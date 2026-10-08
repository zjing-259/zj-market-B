import {createRequire} from 'node:module'
import {resolve,dirname} from 'node:path'
import {fileURLToPath} from 'node:url'
import {mkdir,writeFile,readFile} from 'node:fs/promises'
import assert from 'node:assert/strict'
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..'),base='http://127.0.0.1:5173'
const {chromium}=createRequire(resolve(root,'target/b02-browser-runtime/package.json'))('playwright')
const fixture=JSON.parse(await readFile(resolve(process.env.B_TRIAL_WORK,'fixtures.json'),'utf8'))
const browser=await chromium.launch({headless:true,executablePath:process.env.B_BROWSER_EXECUTABLE})
const context=await browser.newContext({viewport:{width:1280,height:1100}}),page=await context.newPage(),errors=[]
page.on('pageerror',e=>errors.push(e.message))
let trialCount=0,lastTrial
page.on('response',async r=>{if(r.url().endsWith('/trial')&&r.status()===200){trialCount++;lastTrial=(await r.json()).data}})
async function login(role=''){
 await page.locator('#loginName').fill(process.env[`B_TRIAL_TEST_${role}LOGIN_NAME`]);await page.locator('#password').fill(process.env[`B_TRIAL_TEST_${role}PASSWORD`]);await page.getByRole('button',{name:'登录',exact:true}).last().click()
}
async function visit(key){await page.goto(`${base}/products/${fixture[key].goodsId}`);await page.locator('.product-detail').getByRole('heading',{name:fixture[key].goodsName,exact:true}).waitFor()}
async function until(check,description,timeout=20000){const end=Date.now()+timeout;while(!await check()){assert.ok(Date.now()<end,description);await page.waitForTimeout(100)}}
try{
 if(process.argv[2]==='offline'){
  await visit('public');await page.getByRole('link',{name:'登录查看优惠',exact:true}).click();await login()
  await page.getByRole('alert').filter({hasText:'服务暂时不可用'}).waitFor({timeout:20000});assert.equal(await page.getByText('暂无可展示优惠。',{exact:true}).count(),0);assert.equal(await page.locator('.trial-panel dl').count(),0)
  await page.getByRole('button',{name:'重新试算',exact:true}).click();await page.getByRole('alert').filter({hasText:'服务暂时不可用'}).waitFor();assert.equal(new URL(page.url()).pathname,`/products/${fixture.public.goodsId}`)
  await page.getByRole('button',{name:'返回列表',exact:true}).click();await page.getByRole('heading',{name:'在售商品',exact:true}).waitFor();assert.deepEqual(errors,[])
  await writeFile(resolve(root,'target/trial/browser-offline.txt'),'status=PASSED\nactual-A-process-stopped/normal-B-startup-and-public-browse/automatic-trial-error/manual-retrial-error/not-NO_PUBLIC_OFFER/not-login-expired/pageerrors=0\n');console.log('Actual A offline browser: PASSED')
 }else{
 await page.goto(base);await page.getByRole('heading',{name:'在售商品',exact:true}).waitFor()
 await visit('public');await page.getByRole('link',{name:'登录查看优惠',exact:true}).waitFor();assert.equal(trialCount,0)
 await page.getByRole('link',{name:'登录查看优惠',exact:true}).click();await login();await page.locator('.trial-panel').getByText('你当前可参与此优惠。',{exact:true}).waitFor();assert.equal(new URL(page.url()).pathname,`/products/${fixture.public.goodsId}`);assert.equal(lastTrial.offer.payPrice,'90.00')
 const first=trialCount;await page.getByRole('button',{name:'重新试算',exact:true}).click();await until(()=>trialCount===first+1,'one explicit recalculation');await page.getByText('你当前可参与此优惠。',{exact:true}).waitFor()
 await visit('ineligible');await page.getByText('你当前不符合该优惠的参与条件。',{exact:true}).waitFor();assert.equal(lastTrial.state,'INELIGIBLE');assert.equal(lastTrial.offer.payPrice,'90.00')
 for(const key of ['hidden','none']){await visit(key);await page.getByText('暂无可展示优惠。',{exact:true}).waitFor();assert.equal(lastTrial.offer,null);assert.deepEqual(Object.keys(lastTrial).sort(),['goodsId','productVersion','quotedAt','state','offer'].sort());assert.equal(await page.locator('.trial-panel .product-price').count(),0)}
 // Hold an actual A/B quote in transport while an actual operator edits B.
 const operator=await browser.newContext({extraHTTPHeaders:{Origin:base}});const api=operator.request
 const csrf=(await(await api.get(`${base}/api/v1/auth/csrf`)).json()).data
 const loginResponse=await api.post(`${base}/api/v1/auth/login`,{headers:{[csrf.headerName]:csrf.token},data:{loginName:process.env.B_TRIAL_TEST_OP_LOGIN_NAME,password:process.env.B_TRIAL_TEST_OP_PASSWORD}});assert.equal(loginResponse.status(),200,'actual operator login');const signed=(await loginResponse.json()).data
 assert.ok(signed.accessToken);const headers={Authorization:`Bearer ${signed.accessToken}`}
 const id=fixture.race.goodsId
 let heldResolve,releaseResolve
 const held=new Promise(r=>heldResolve=r),release=new Promise(r=>releaseResolve=r)
 let once=true
 await page.route(`**/products/${id}/trial`,async route=>{
  if(!once){await route.continue();return}once=false
  const response=await route.fetch();assert.equal(response.status(),200);const body=await response.json();heldResolve(body.data);await release;await route.fulfill({response})
 })
 const navigation=visit('race');const old=await held;await navigation
 const before=(await(await api.get(`${base}/api/v1/admin/products/${id}`,{headers})).json()).data
 const edited=(await(await api.put(`${base}/api/v1/admin/products/${id}`,{headers,data:{goodsName:before.goodsName,description:'浏览器在途真实修改',imageUrl:before.imageUrl,originalPrice:before.originalPrice,currency:'CNY',saleStatus:before.saleStatus,expectedVersion:before.productVersion}})).json()).data
 assert.notEqual(edited.productVersion,old.productVersion)
 releaseResolve();await page.getByText(`在售 · 商品版本 ${edited.productVersion}`,{exact:true}).waitFor()
 await page.getByText('你当前可参与此优惠。',{exact:true}).waitFor({timeout:65000});assert.equal(lastTrial.productVersion,edited.productVersion)
 await page.unroute(`**/products/${id}/trial`)
 // A paused, owned product verifies the real 60-second bound without fake timers.
 let pending
 for(let attempt=0;attempt<3&&!pending;attempt++){
  const created=(await(await api.post(`${base}/api/v1/admin/products`,{headers,data:{goodsName:'限时刷新-'+Date.now(),description:'自有暂停样本',imageUrl:null,originalPrice:'100.00',currency:'CNY',saleStatus:'ON_SALE'}})).json()).data
  const paused=await api.post(`${base}/api/v1/admin/products/${created.goodsId}/sync/pauses`,{headers,data:{eventId:created.sync.targetEventId,expectedVersion:created.productVersion}})
  if(paused.status()===200)pending=created
 }
 assert.ok(pending,'own sample paused before background send')
 let reads=0,quotes=0
 const count=r=>{if(r.url().endsWith(`/products/${pending.goodsId}`)&&r.request().method()==='GET')reads++;if(r.url().endsWith(`/products/${pending.goodsId}/trial`))quotes++}
 page.on('response',count)
 await page.goto(`${base}/products/${pending.goodsId}`);await page.getByText('每 3 秒刷新商品资料，最多等待 1 分钟。',{exact:true}).waitFor()
 await page.getByText('自动刷新已结束，可手动刷新商品资料。',{exact:true}).waitFor({timeout:65000})
 assert.ok(reads>=18&&reads<=21,'bounded three-second public reads');assert.equal(quotes,0,'no trial before confirmed sync')
 const settled=reads;await page.waitForTimeout(3500);assert.equal(reads,settled,'no read after deadline')
 const resumed=await api.post(`${base}/api/v1/admin/products/${pending.goodsId}/sync/retries`,{headers,data:{eventId:pending.sync.targetEventId,expectedVersion:pending.productVersion}});assert.equal(resumed.status(),202)
 await until(async()=>{const r=await api.get(`${base}/api/v1/products/${pending.goodsId}`);return (await r.json()).data.syncReady},'real A confirms resumed product',30000)
 await page.getByRole('button',{name:'刷新商品资料',exact:true}).click();await page.getByText('暂无可展示优惠。',{exact:true}).waitFor();assert.equal(quotes,1,'manual refresh restores automatic real trial')
 page.off('response',count);await operator.close()
 assert.equal(await page.getByRole('button',{name:/购买|支付|下单/}).count(),0)
 assert.deepEqual(await page.evaluate(()=>[localStorage.length,sessionStorage.length]),[0,0])
 await mkdir(resolve(root,'target/trial'),{recursive:true});await page.screenshot({path:resolve(root,'target/trial/store.png'),fullPage:true})
 await page.getByRole('button',{name:'账号中心',exact:true}).click();await page.getByRole('button',{name:'退出登录',exact:true}).click();await page.locator('#loginName').waitFor()
 await page.goto(`${base}/login?returnTo=${encodeURIComponent('/products/'+fixture.hidden.goodsId)}`);await login('MEMBER_');await page.getByText('你当前可参与此优惠。',{exact:true}).waitFor();assert.equal(lastTrial.goodsId,fixture.hidden.goodsId)
 await page.getByRole('button',{name:'账号中心',exact:true}).click();await page.getByRole('button',{name:'退出登录',exact:true}).click();await page.locator('#loginName').waitFor();await visit('hidden');await page.getByRole('link',{name:'登录查看优惠',exact:true}).waitFor();assert.equal(await page.locator('.trial-panel dl').count(),0)
 await page.goto(`${base}/login?returnTo=https%3A%2F%2Fevil.invalid`);await login();await page.getByRole('button',{name:'退出登录',exact:true}).waitFor();assert.equal(new URL(page.url()).pathname,'/login');assert.equal(new URL(page.url()).origin,base)
 assert.deepEqual(errors,[])
 await writeFile(resolve(root,'target/trial/browser.txt'),'status=PASSED\nactual-Edge/anonymous-base/login-safe-return/automatic-real-A-trial/manual-retrial/visible-ineligible/hidden-no-offer/member-identity/logout-clears/no-token-storage/actual-delayed-quote-concurrent-operator-edit/discard-old-version/pending-refresh-auto-retrial/actual-60s-limit-public-read-only/manual-refresh-after-confirmation/no-orders/pageerrors=0\n')
 console.log('B-02.5 actual trial browser verification: PASSED')
 }
}finally{await browser.close()}
