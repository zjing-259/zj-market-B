import {createRequire} from 'node:module'
import {resolve,dirname} from 'node:path'
import {fileURLToPath} from 'node:url'
import {readFile,mkdir,writeFile} from 'node:fs/promises'
import {randomUUID} from 'node:crypto'
import assert from 'node:assert/strict'
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..'),output=resolve(root,'target/closes')
await mkdir(output,{recursive:true})
const fixture=JSON.parse(await readFile(resolve(root,'target/orders/browser-fixtures.json'),'utf8'))
const {chromium}=createRequire(resolve(root,'target/b02-browser-runtime/package.json'))('playwright')
const profile=resolve(output,'profile-'+randomUUID()),errors=[],origin='http://127.0.0.1:5173'
const launch=()=>chromium.launchPersistentContext(profile,{headless:true,executablePath:process.env.B_BROWSER_EXECUTABLE,viewport:{width:1400,height:1000}})
let ctx=await launch(),page=await ctx.newPage()
const observe=()=>page.on('pageerror',e=>errors.push(e.message))
async function login(){await page.goto(origin+'/login');await page.locator('#loginName').fill(process.env.B_BROWSER_OPERATOR_LOGIN_NAME);await page.locator('#password').fill(process.env.B_BROWSER_OPERATOR_PASSWORD);await page.getByRole('button',{name:'登录',exact:true}).last().click();await page.getByRole('button',{name:'退出登录',exact:true}).waitFor()}
const actions=()=>page.evaluate(()=>Object.keys(localStorage).filter(k=>k.startsWith('b-order-action:')).map(k=>JSON.parse(localStorage.getItem(k))))
try{
 observe();await login()
 const orders=await page.evaluate(async()=>(await import('/src/services/auth.ts')).request('/orders?size=100'))
 const order=orders.items.find(o=>o.product.goodsId===fixture.goodsId)
 assert.ok(order,'existing browser OPEN order')
 await page.goto(origin+'/orders/'+order.orderId);await page.getByRole('button',{name:'确认取消未支付订单',exact:true}).waitFor()
 let originalCancel
 await page.route('**/api/v1/orders/*/cancel',async route=>{originalCancel=route.request().postDataJSON();const result=await route.fetch();assert.ok([200,202].includes(result.status()));await route.abort('failed')})
 await page.getByRole('button',{name:'确认取消未支付订单',exact:true}).click();await page.getByRole('button',{name:'重试原取消',exact:true}).waitFor();assert.equal((await actions())[0].body.operationId,originalCancel.operationId)
 await ctx.close();ctx=await launch();page=await ctx.newPage();observe();await page.goto(origin+'/orders/'+order.orderId)
 await page.getByRole('button',{name:'重试原取消',exact:true}).waitFor();assert.deepEqual((await actions())[0].body,originalCancel)
 let retried;await page.route('**/api/v1/orders/*/cancel',async route=>{retried=route.request().postDataJSON();await route.continue()})
 await page.getByRole('button',{name:'重试原取消',exact:true}).click();await page.getByRole('button',{name:'重试原取消',exact:true}).waitFor({state:'hidden'});await page.getByText(/库存已释放/).waitFor();assert.deepEqual(retried,originalCancel);assert.equal((await actions()).length,0)
 const stock=await page.evaluate(async id=>(await import('/src/services/auth.ts')).request('/admin/inventory/'+id),fixture.goodsId);assert.equal(stock.reserved,'1');assert.equal(stock.available,'9')
 await page.screenshot({path:resolve(output,'closed.png'),fullPage:true})
 await page.goto(origin+'/admin/orders/'+fixture.exceptionOrderId);await page.getByRole('button',{name:'暂停恢复',exact:true}).waitFor();await page.getByLabel('操作原因').fill('browser controlled pause')
 let originalControl;await page.route('**/api/v1/admin/orders/*/coordination-controls',async route=>{originalControl=route.request().postDataJSON();const result=await route.fetch();assert.equal(result.status(),202);await route.abort('failed')})
 await page.getByRole('button',{name:'暂停恢复',exact:true}).click();await page.getByRole('button',{name:'重试原控制',exact:true}).waitFor()
 await ctx.close();ctx=await launch();page=await ctx.newPage();observe();await page.goto(origin+'/admin/orders/'+fixture.exceptionOrderId)
 await page.getByRole('button',{name:'重试原控制',exact:true}).waitFor();assert.deepEqual((await actions())[0].body,originalControl)
 let controlRetry;await page.route('**/api/v1/admin/orders/*/coordination-controls',async route=>{controlRetry=route.request().postDataJSON();await route.continue()})
 await page.getByRole('button',{name:'重试原控制',exact:true}).click();await page.getByRole('button',{name:'重试原控制',exact:true}).waitFor({state:'hidden'});await page.getByText(/已暂停/).waitFor();assert.deepEqual(controlRetry,originalControl);assert.equal((await actions()).length,0)
 await page.getByLabel('操作原因').fill('browser resume original task');await page.getByRole('button',{name:'恢复原任务',exact:true}).click();await page.getByText(/未暂停/).waitFor()
 await page.getByLabel('操作原因').fill('browser read only original query');await page.getByRole('button',{name:'立即核对',exact:true}).click();await page.getByText(/任务 QUERY/).waitFor()
 const summary=await page.evaluate(async id=>(await import('/src/services/auth.ts')).request('/admin/orders/'+id+'/coordination'),fixture.exceptionOrderId)
 assert.ok(!('leaseToken' in summary)&&!('reserveRequest' in summary)&&!('closeRequest' in summary));assert.equal(await page.getByRole('button',{name:/强制|释放库存|付款/}).count(),0)
 await page.screenshot({path:resolve(output,'operator.png'),fullPage:true});assert.deepEqual(errors,[])
 await writeFile(resolve(output,'browser.json'),JSON.stringify({status:'PASSED',checks:['real B cancel committed response lost','actual browser close and reopen restores original cancel identity','same original cancel retry releases once','OP pause committed response lost','actual browser reopen restores original control body/version/key','original control retry then resume and read only query','safe attempt summaries and no force release/payment UI'],pageErrors:errors,port:'verification-only controlled A; real A checked separately'},null,2))
 console.log('Unpaid close and operator browser acceptance: PASSED')
}finally{await ctx.close()}
