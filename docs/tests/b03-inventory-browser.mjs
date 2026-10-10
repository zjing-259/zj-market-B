import {createRequire} from 'node:module'
import {resolve,dirname} from 'node:path'
import {fileURLToPath} from 'node:url'
import {mkdir,writeFile} from 'node:fs/promises'
import {randomUUID} from 'node:crypto'
import assert from 'node:assert/strict'
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..')
const {chromium}=createRequire(resolve(root,'target/b02-browser-runtime/package.json'))('playwright')
const output=resolve(root,'target/inventory')
await mkdir(output,{recursive:true})
const profile=resolve(output,'profile-'+randomUUID())
const launch=()=>chromium.launchPersistentContext(profile,{headless:true,executablePath:process.env.B_BROWSER_EXECUTABLE??'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',viewport:{width:1400,height:1000}})
let ctx=await launch(),page=await ctx.newPage()
const errors=[],writes=[]
function observe(p){p.on('pageerror',e=>errors.push(e.message));p.on('request',r=>{if(r.method()==='POST'&&/\/admin\/inventory\/[^/]+\/(?:inbounds|adjustments)$/.test(r.url()))writes.push(JSON.parse(r.postData()))})}
observe(page)
async function login(p,other=false){
 await p.goto('http://127.0.0.1:5173/login')
 await p.locator('#loginName').fill(process.env[other?'B_BROWSER_OTHER_LOGIN_NAME':'B_BROWSER_OPERATOR_LOGIN_NAME'])
 await p.locator('#password').fill(process.env[other?'B_BROWSER_OTHER_PASSWORD':'B_BROWSER_OPERATOR_PASSWORD'])
 await p.getByRole('button',{name:'登录',exact:true}).last().click()
 await p.getByRole('button',{name:'库存管理',exact:true}).waitFor()
}
async function inventory(p,id){
 await p.goto('http://127.0.0.1:5173/admin/inventory')
 await p.getByRole('heading',{name:'库存管理',exact:true}).waitFor()
 await p.locator('[name=inventorySearch]').fill(id)
 await p.getByRole('button',{name:'查询库存',exact:true}).click()
 await p.getByRole('row').filter({hasText:id}).getByRole('button',{name:'维护库存'}).click()
 await p.locator('[name=inventoryDelta]').waitFor()
}
async function balance(p,id){return p.evaluate(async id=>(await import('/src/services/auth.ts')).request('/admin/inventory/'+id),id)}
async function form(p,quantity,adjust=false){
 await p.locator('form select').selectOption(adjust?'ADJUST':'INBOUND')
 await p.locator('[name=inventoryDelta]').fill(quantity);await p.locator('[name=inventoryReason]').fill('浏览器库存验收')
 await p.getByRole('button',{name:'确认提交',exact:true}).click()
}
const pending=async p=>p.evaluate(()=>{const out=[];for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(k.startsWith('b-inventory-pending:'))out.push(JSON.parse(localStorage.getItem(k)))}return out})
try{
 await login(page)
 const product=await page.evaluate(async ()=>{const a=await import('/src/services/auth.ts');return a.write('/admin/products','POST',{goodsName:'库存浏览器验收',originalPrice:'12.34',currency:'CNY'})})
 const id=product.goodsId
 await inventory(page,id);await form(page,'100')
 await page.getByRole('status').filter({hasText:'已成功'}).waitFor()
 assert.equal((await balance(page,id)).available,'100')
 assert.equal((await pending(page)).length,0)
 // Backend commits but browser loses the response. Suppress result queries temporarily.
 const writePattern='**/api/v1/admin/inventory/'+id+'/inbounds',queryPattern='**/api/v1/admin/inventory/operations/*'
 const lose=async route=>{const r=await route.fetch();assert.ok([200,201].includes(r.status()));await route.abort('failed')}
 await page.route(queryPattern,r=>r.abort('failed'));await page.route(writePattern,lose)
 await form(page,'7')
 await page.getByRole('heading',{name:'待核对操作',exact:true}).waitFor()
 await page.waitForFunction(()=>[...document.querySelectorAll('button')].some(b=>b.textContent==='重试原操作'&&!b.disabled))
 await page.getByRole('button',{name:'先核对原操作',exact:true}).waitFor()
 assert.equal((await balance(page,id)).available,'107')
 let records=await pending(page);assert.equal(records.length,1)
 const original=records[0];assert.equal(original.request.delta,'7')
 assert.ok(!JSON.stringify(records).match(/accessToken|refreshToken|password|eyJ/))
 const before=writes.length
 const tab=await ctx.newPage();observe(tab);await tab.route(queryPattern,r=>r.abort('failed'));await inventory(tab,id)
 await tab.getByRole('button',{name:'先核对原操作',exact:true}).waitFor()
 const blocked=await tab.evaluate(async q=>{try{await(await import('/src/services/inventory.ts')).submitInventory(q);return false}catch{return true}}, {...original.request,delta:'1'})
 assert.ok(blocked);assert.equal(writes.length,before)
 await tab.close()
 await page.reload();await page.getByRole('heading',{name:'待核对操作',exact:true}).waitFor()
 assert.equal((await pending(page))[0].operationId,original.operationId)
 // Close the actual browser context and reopen the same persistent profile.
 await ctx.close();ctx=await launch();page=await ctx.newPage();observe(page);await page.route(queryPattern,r=>r.abort('failed'))
 await page.goto('http://127.0.0.1:5173/admin/inventory')
 await page.getByRole('heading',{name:'待核对操作',exact:true}).waitFor()
 assert.equal((await pending(page))[0].operationId,original.operationId)
 // Another operator cannot see/retry the previous operator's pending task.
 await page.getByRole('button',{name:'账号中心',exact:true}).click();await page.getByRole('button',{name:'退出登录',exact:true}).click()
 await page.waitForFunction(()=>{const input=document.querySelector('#loginName');return input&&!input.disabled})
 await login(page,true);await page.getByRole('button',{name:'库存管理',exact:true}).click()
 await page.getByRole('heading',{name:'库存管理',exact:true}).waitFor()
 assert.equal(await page.getByRole('heading',{name:'待核对操作',exact:true}).count(),0)
 assert.equal((await pending(page)).length,1)
 await page.getByRole('button',{name:'账号中心',exact:true}).click();await page.getByRole('button',{name:'退出登录',exact:true}).click()
 await page.waitForFunction(()=>{const input=document.querySelector('#loginName');return input&&!input.disabled})
 await login(page);await page.getByRole('button',{name:'库存管理',exact:true}).click()
 await page.getByRole('heading',{name:'待核对操作',exact:true}).waitFor()
 await page.unroute(queryPattern);await page.getByRole('button',{name:'查询原结果',exact:true}).click()
 await page.getByRole('status').filter({hasText:'已成功'}).waitFor()
 assert.equal((await pending(page)).length,0);assert.equal((await balance(page,id)).available,'107')
 // Repeat a lost-response operation manually, exactly the same body/key.
 await inventory(page,id);await page.route(queryPattern,r=>r.abort('failed'));await page.route(writePattern,lose);await form(page,'1')
 await page.getByRole('heading',{name:'待核对操作',exact:true}).waitFor()
 await page.waitForFunction(()=>[...document.querySelectorAll('button')].some(b=>b.textContent==='重试原操作'&&!b.disabled))
 const old=(await pending(page))[0]
 await page.unroute(writePattern)
 await page.getByRole('button',{name:'重试原操作',exact:true}).click()
 await page.getByRole('status').filter({hasText:'已成功'}).waitFor()
 assert.equal((await balance(page,id)).available,'108');assert.equal((await pending(page)).length,0)
 const retries=writes.filter(w=>w.operationId===old.operationId);assert.equal(retries.length,2);assert.deepEqual(retries[0],retries[1])
 await page.unroute(queryPattern)
 await inventory(page,id);await form(page,'-1000',true)
 await page.getByRole('status').filter({hasText:'已拒绝'}).waitFor()
 assert.equal((await pending(page)).length,0);assert.equal((await balance(page,id)).available,'108')
 await page.screenshot({path:resolve(output,'operator.png'),fullPage:true})
 assert.deepEqual(errors,[])
 await writeFile(resolve(output,'browser.json'),JSON.stringify({status:'PASSED',checks:['off-sale inbound','response loss committed once','reload recovery','actual browser close/reopen recovery','cross-tab same SKU blocked','identity isolation','manual original-key retry','durable rejection resolves pending'],pageErrors:errors},null,2))
 console.log('B inventory real browser acceptance: PASSED')
}finally{await ctx.close()}
