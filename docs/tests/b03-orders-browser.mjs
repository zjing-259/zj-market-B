import {createRequire} from 'node:module'
import {resolve,dirname} from 'node:path'
import {fileURLToPath} from 'node:url'
import {readFile,mkdir,writeFile} from 'node:fs/promises'
import {randomUUID} from 'node:crypto'
import assert from 'node:assert/strict'
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..')
const {chromium}=createRequire(resolve(root,'target/b02-browser-runtime/package.json'))('playwright')
const output=resolve(root,'target/orders');await mkdir(output,{recursive:true})
const fixture=JSON.parse(await readFile(resolve(output,'browser-fixtures.json'),'utf8'))
const profile=resolve(output,'profile-'+randomUUID()),errors=[]
const launch=()=>chromium.launchPersistentContext(profile,{headless:true,executablePath:process.env.B_BROWSER_EXECUTABLE,viewport:{width:1400,height:1000}})
let ctx=await launch(),page=await ctx.newPage()
function observe(p){p.on('pageerror',e=>errors.push(e.message))}
async function login(p,other=false){await p.goto('http://127.0.0.1:5173/login');await p.locator('#loginName').fill(process.env[other?'B_BROWSER_OTHER_LOGIN_NAME':'B_BROWSER_OPERATOR_LOGIN_NAME']);await p.locator('#password').fill(process.env[other?'B_BROWSER_OTHER_PASSWORD':'B_BROWSER_OPERATOR_PASSWORD']);await p.getByRole('button',{name:'登录',exact:true}).last().click();await p.getByRole('button',{name:'退出登录',exact:true}).waitFor()}
async function trial(p){await p.route('**/api/v1/products/*/trial',route=>route.fulfill({json:{code:'0000',message:'controlled UI quote only',requestId:randomUUID(),data:{goodsId:fixture.goodsId,productVersion:'1',quotedAt:new Date().toISOString(),state:'AVAILABLE',offer:fixture.offer}}}))}
const pending=p=>p.evaluate(()=>Object.keys(localStorage).filter(k=>k.startsWith('b-purchase:')).map(k=>JSON.parse(localStorage.getItem(k))))
try{
 observe(page);await login(page);await trial(page);await page.goto('http://127.0.0.1:5173/products/'+fixture.goodsId)
 await page.getByRole('button',{name:'核对开团报价',exact:true}).waitFor();await page.getByRole('button',{name:'核对开团报价',exact:true}).click();await page.getByRole('button',{name:'确认购买',exact:true}).waitFor()
 await page.route('**/api/v1/orders/by-intent/*',r=>r.abort('failed'))
 await page.route('**/api/v1/orders',async route=>{if(route.request().method()==='POST'){const r=await route.fetch();assert.equal(r.status(),202);await route.abort('failed')}else await route.continue()})
 await page.getByRole('button',{name:'确认购买',exact:true}).click();await page.getByRole('button',{name:'用原编号重试',exact:true}).waitFor();await page.waitForFunction(()=>![...document.querySelectorAll('button')].find(b=>b.textContent==='用原编号重试')?.disabled)
 const original=(await pending(page))[0];assert.ok(original?.purchaseIntentId)
 // Actual browser close/reopen with its disk profile, not an approximate storageState.
 await ctx.close();ctx=await launch();page=await ctx.newPage();observe(page);await page.route('**/api/v1/orders/by-intent/*',r=>r.abort('failed'));await trial(page);await page.goto('http://127.0.0.1:5173/products/'+fixture.goodsId)
 await page.getByRole('button',{name:'用原编号重试',exact:true}).waitFor();assert.equal((await pending(page))[0].purchaseIntentId,original.purchaseIntentId)
 await page.unroute('**/api/v1/orders/by-intent/*');await page.getByRole('button',{name:'查询原购买',exact:true}).click();await page.getByRole('link',{name:'查看原订单',exact:true}).waitFor()
 const href=await page.getByRole('link',{name:'查看原订单',exact:true}).getAttribute('href');await page.getByRole('link',{name:'查看原订单',exact:true}).click();await page.getByText('支付暂未开放。',{exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:/^(支付|付款|立即支付|确认支付)$/}).count(),0)
 const stock=await page.evaluate(async id=>(await import('/src/services/auth.ts')).request('/admin/inventory/'+id),fixture.goodsId);assert.equal(stock.available,'9');assert.equal(stock.reserved,'1');assert.equal((await pending(page)).length,0)
 await page.screenshot({path:resolve(output,'detail.png'),fullPage:true})
 await page.goto('http://127.0.0.1:5173/orders');await page.getByRole('link',{name:'查看订单',exact:true}).first().waitFor()
 await page.getByRole('button',{name:'账号中心',exact:true}).click();await page.getByRole('button',{name:'退出登录',exact:true}).click();await page.locator('#loginName').waitFor();await page.waitForFunction(()=>!document.querySelector('#loginName')?.disabled)
 await login(page,true);await page.goto('http://127.0.0.1:5173'+href);await page.getByRole('alert').filter({hasText:'暂未查到原购买'}).waitFor();assert.equal(await page.getByText('支付暂未开放。',{exact:true}).count(),0)
 assert.deepEqual(errors,[])
 await writeFile(resolve(output,'browser.json'),JSON.stringify({status:'PASSED',checks:['real HTTP confirmation/create/stock reserve','committed response lost','same original intent after actual browser reopen','original intent query recovery','one held unit only','owner list/detail','cross-user detail hidden','no payment button'],pageErrors:errors,quote:'controlled UI trial and verification-only quote port; real A separately tested'},null,2))
 console.log('Local order browser acceptance: PASSED')
}finally{await ctx.close()}
