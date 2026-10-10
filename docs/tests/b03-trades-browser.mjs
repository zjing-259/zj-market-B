import {createRequire} from 'node:module'
import {resolve,dirname} from 'node:path'
import {fileURLToPath} from 'node:url'
import {readFile,mkdir,writeFile} from 'node:fs/promises'
import {randomUUID} from 'node:crypto'
import assert from 'node:assert/strict'
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..'),output=resolve(root,'target/trades')
await mkdir(output,{recursive:true})
const fixture=JSON.parse(await readFile(resolve(root,'target/orders/browser-fixtures.json'),'utf8'))
const {chromium}=createRequire(resolve(root,'target/b02-browser-runtime/package.json'))('playwright')
const browser=await chromium.launch({headless:true,executablePath:process.env.B_BROWSER_EXECUTABLE}),context=await browser.newContext({viewport:{width:1400,height:1000}}),page=await context.newPage(),errors=[]
page.on('pageerror',e=>errors.push(e.message))
const origin='http://127.0.0.1:5173',team='team-browser'
try{
 await page.route('**/api/v1/products/*/trial',route=>route.fulfill({json:{code:'0000',message:'controlled UI quote',requestId:randomUUID(),data:{goodsId:fixture.goodsId,productVersion:'1',quotedAt:new Date().toISOString(),state:'AVAILABLE',offer:fixture.offer}}}))
 await page.goto(origin+'/teams/'+team);await page.getByText('请登录后查看团队详情。',{exact:false}).waitFor();assert.equal(await page.getByRole('button',{name:'核对参团报价',exact:true}).count(),0)
 await page.getByRole('link',{name:'去登录',exact:true}).click();await page.locator('#loginName').fill(process.env.B_BROWSER_OTHER_LOGIN_NAME);await page.locator('#password').fill(process.env.B_BROWSER_OTHER_PASSWORD);await page.getByRole('button',{name:'登录',exact:true}).last().click();await page.getByRole('button',{name:'核对参团报价',exact:true}).waitFor();assert.match(page.url(),/\/teams\/team-browser$/)
 // A changed quote is shown, but no purchase is sent until a fresh explicit confirmation.
 let creates=0;page.on('request',r=>{if(r.method()==='POST'&&new URL(r.url()).pathname==='/api/v1/orders')creates++})
 await page.route('**/api/v1/purchase-confirmations',route=>route.fulfill({status:409,json:{code:'OFFER_CHANGED',message:'changed',requestId:randomUUID(),data:{latestOffer:{...fixture.offer,payPrice:'8.00',deductionPrice:'2.00'}}}}))
 await page.getByRole('button',{name:'核对参团报价',exact:true}).click();await page.getByText(/最新试算金额 ¥ 8.00/).waitFor();assert.equal(creates,0);assert.equal(await page.getByRole('button',{name:'确认购买',exact:true}).count(),0)
 await page.unroute('**/api/v1/purchase-confirmations');await page.getByRole('button',{name:'刷新团队并重新试算',exact:true}).click();await page.getByRole('button',{name:'核对参团报价',exact:true}).waitFor();await page.getByRole('button',{name:'核对参团报价',exact:true}).click();await page.getByText(/确认加入此团队/).waitFor();await page.getByRole('button',{name:'确认购买',exact:true}).click();await page.getByRole('link',{name:'查看原订单',exact:true}).waitFor();await page.getByRole('link',{name:'查看原订单',exact:true}).click();await page.getByText(/待支付/).first().waitFor();await page.getByText(/A 确认的支付期限/).waitFor();assert.equal(creates,1);assert.equal(await page.getByRole('button',{name:/^(支付|付款|立即支付|确认支付)$/}).count(),0)
 const saved=await page.evaluate(async()=>{const auth=await import('/src/services/auth.ts');return auth.request('/orders/'+location.pathname.split('/')[2])});assert.equal(saved.mode,'JOIN');assert.equal(saved.requestedTeamId,team);assert.equal(saved.teamId,team);assert.equal(saved.offer.payPrice,'9.00');assert.equal(saved.paymentEnabled,false)
 await page.screenshot({path:resolve(output,'waiting-payment.png'),fullPage:true});await page.getByRole('link',{name:'查看团队与分享链接',exact:true}).click();await page.getByText('分享地址：',{exact:false}).waitFor()
 await page.goto(origin+'/teams/team-full');await page.getByText('团队当前不可加入，不会改为新开团。',{exact:true}).waitFor();await page.waitForFunction(()=>{const b=[...document.querySelectorAll('button')].find(b=>b.textContent==='核对参团报价');return !b||b.disabled});assert.equal(creates,1)
 await page.goto(origin+'/teams/team-other-activity');await page.getByRole('alert').filter({hasText:'当前活动或成团条件与此团队不一致'}).waitFor();assert.equal(creates,1)
 assert.deepEqual(errors,[])
 await writeFile(resolve(output,'browser.json'),JSON.stringify({status:'PASSED',checks:['login required and return to shared team','changed quote displayed with no silent purchase','explicit refreshed quote and JOIN','real B HTTP order fields and WAITING_PAYMENT polling','same candidate team and frozen price','share URL and A deadline','full team never falls back OPEN','activity mismatch blocks purchase','payment remains disabled'],pageErrors:errors,port:'verification-only controlled A port; real A separately validated'},null,2));console.log('Trade team browser acceptance: PASSED')
}finally{await browser.close()}
