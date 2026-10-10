import {createRequire} from 'node:module'
import {readFile,writeFile} from 'node:fs/promises'
import {resolve} from 'node:path'
import assert from 'node:assert/strict'
const root=process.cwd(),work=process.env.B_PAYMENT_BROWSER_WORK
assert.ok(work)
const fixture=JSON.parse(await readFile(resolve(work,'browser-private.json'),'utf8'))
const {chromium}=createRequire(resolve(root,'target/b02-browser-runtime/package.json'))('playwright')
const browser=await chromium.launch({headless:true,executablePath:process.env.B_BROWSER_EXECUTABLE??'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'})
const context=await browser.newContext({viewport:{width:1280,height:900}}),page=await context.newPage(),errors=[]
page.on('pageerror',e=>errors.push(e.message))
const path=`/orders/${fixture.orderId}/payment`,writes=[]
context.on('request',r=>{if(r.method()==='POST'&&/payment-attempts|simulated-results/.test(r.url()))writes.push(JSON.parse(r.postData()))})
async function login(tab,name){await tab.goto('http://127.0.0.1:5173/login?returnTo='+encodeURIComponent(path));await tab.getByLabel('登录名',{exact:true}).fill(name);await tab.getByLabel('密码',{exact:true}).fill(fixture.password);await tab.locator('form').getByRole('button',{name:'登录',exact:true}).click();await tab.waitForURL('**'+path)}
try{
 await page.goto('http://127.0.0.1:5173'+path);await page.getByText('请登录后查看本人收银台。').waitFor()
 await login(page,fixture.loginName)
 await page.getByText('尚未创建支付单。',{exact:true}).waitFor()
 // Drop a committed write's response, then simulate a misleading read miss. Neither permits a fresh key.
 await page.route('**/payment-operations/*',route=>route.fulfill({status:404,contentType:'application/json',body:JSON.stringify({code:'PAYMENT_OPERATION_NOT_FOUND',info:'owned read miss',data:null,requestId:'browser-owned-404'})}))
 let lost=false
 await page.route('**/payment-attempts',async route=>{if(!lost){lost=true;await route.fetch();await route.abort('failed')}else await route.continue()})
 await page.getByRole('button',{name:'创建模拟支付尝试',exact:true}).click();await page.getByRole('button',{name:'重试原操作',exact:true}).waitFor()
 assert.equal(writes.length,1)
 const original=writes[0]
 await page.reload();await page.getByRole('button',{name:'重试原操作',exact:true}).waitFor();assert.equal(writes.length,1)
 await page.getByRole('button',{name:'重试原操作',exact:true}).click();await page.getByText('原操作编号：',{exact:false}).waitFor();assert.equal(writes.length,2);assert.deepEqual(writes[1],original)
 await page.unroute('**/payment-operations/*');await page.getByRole('button',{name:'查询支付状态',exact:true}).click();await page.getByRole('button',{name:'选择模拟失败',exact:true}).waitFor()
 await page.getByRole('button',{name:'选择模拟失败',exact:true}).click();await page.getByRole('button',{name:'重新尝试模拟支付',exact:true}).waitFor()
 await page.getByRole('button',{name:'重新尝试模拟支付',exact:true}).click();await page.getByRole('button',{name:'选择模拟成功',exact:true}).waitFor()
 const second=await context.newPage();second.on('pageerror',e=>errors.push(e.message));await second.goto('http://127.0.0.1:5173'+path);await second.getByRole('button',{name:'选择模拟失败',exact:true}).waitFor()
 const before=writes.length
 // Delay the first write until the second tab has checked the shared, owner-bound pending journal.
 await page.route('**/payment-operations/*',route=>route.fulfill({status:404,contentType:'application/json',body:JSON.stringify({code:'PAYMENT_OPERATION_NOT_FOUND',info:'owned pending read',data:null,requestId:'browser-owned-pending'})}))
 let release;const waiting=new Promise(resolve=>{release=resolve})
 await page.route('**/simulated-results',async route=>{await waiting;await route.continue()})
 await page.getByRole('button',{name:'选择模拟成功',exact:true}).click()
 await second.getByRole('button',{name:'选择模拟失败',exact:true}).click();release();await second.getByRole('alert').filter({hasText:'请先核对原支付操作'}).waitFor()
 await page.getByText('渠道已成功，等待商城同步',{exact:true}).waitFor();assert.equal(writes.length,before+1)
 await page.unroute('**/payment-operations/*');await page.getByRole('button',{name:'查询支付状态',exact:true}).click();await page.getByRole('button',{name:'重试原操作',exact:true}).waitFor({state:'hidden'})
 const stored=await page.evaluate(()=>({local:Object.fromEntries(Object.entries(localStorage)),session:Object.fromEntries(Object.entries(sessionStorage))}))
 assert.ok(!JSON.stringify(stored).includes('accessToken'));assert.ok(!JSON.stringify(stored).includes('refreshToken'))
 await page.screenshot({path:resolve(work,'cashier-desktop.png'),fullPage:true})
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:resolve(work,'cashier-mobile.png'),fullPage:true})
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),'mobile has no horizontal overflow')
 // Switching the shared login must never replay the first owner's pending operation.
 await second.goto('http://127.0.0.1:5173/login');await second.getByRole('button',{name:'退出登录',exact:true}).click();await login(second,fixture.otherLoginName);await second.getByRole('alert').waitFor();assert.equal(writes.length,before+1)
 assert.deepEqual(errors,[])
 await writeFile(resolve(work,'browser.json'),JSON.stringify({status:'PASSED',browser:'Edge headless',checks:['anonymous/login-return','response-loss/read-404/reload-no-write/original-key-retry','failed-attempt/retry','two-tabs-owner-journal/result-choice','channel-success-market-sync-pending','account-switch-no-replay','tokens-not-in-web-storage','desktop/mobile-no-overflow'],pageErrors:0},null,2))
 console.log('Payment browser verification: PASSED')
}finally{await browser.close()}
