import {createRequire} from 'node:module'
import {resolve,dirname} from 'node:path'
import {fileURLToPath} from 'node:url'
import {mkdir,writeFile,readFile} from 'node:fs/promises'
import assert from 'node:assert/strict'
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..')
const {chromium}=createRequire(resolve(root,'target/b02-browser-runtime/package.json'))('playwright')
const fixture=JSON.parse(await readFile(resolve(process.env.B_SYNC_WORK,'browser-fixture.json'),'utf8'))
const browser=await chromium.launch({headless:true,executablePath:process.env.B_BROWSER_EXECUTABLE??'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'})
const context=await browser.newContext({viewport:{width:1440,height:1100}}),page=await context.newPage(),errors=[]
page.on('pageerror',e=>errors.push(e.message))
let quarantine
page.on('response',async response=>{if(response.url().includes('/admin/sync/quarantine') && response.status()===200)quarantine=(await response.json()).data})
try{
 await page.goto('http://127.0.0.1:5173/login');await page.locator('#loginName').fill(process.env.B_BROWSER_OPERATOR_LOGIN_NAME);await page.locator('#password').fill(process.env.B_BROWSER_OPERATOR_PASSWORD);await page.getByRole('button',{name:'登录',exact:true}).last().click();await page.getByRole('button',{name:'商品管理',exact:true}).waitFor()
 await page.goto(`http://127.0.0.1:5173/admin/products/${fixture.goodsId}`);await page.locator('.product-detail').getByRole('heading',{name:'运营同步页面验收',exact:true}).waitFor()
 await page.getByRole('button',{name:'读取同步状态',exact:true}).click();await page.getByText('自动同步已暂停。',{exact:true}).waitFor()
 await page.getByRole('button',{name:'核对并恢复同步',exact:true}).click();await page.getByText('原同步记录已恢复，等待营销端确认。',{exact:true}).waitFor()
 await page.getByRole('button',{name:'暂停自动同步',exact:true}).click();await page.getByText('已暂停自动同步。',{exact:true}).waitFor();await page.getByText('自动同步已暂停。',{exact:true}).waitFor()
 await page.getByRole('button',{name:'核对并恢复同步',exact:true}).click()
 const deadline=Date.now()+90000
 while(!await page.getByText('营销同步：已确认',{exact:false}).count()){
  assert.ok(Date.now()<deadline,'background worker eventually confirms current version');await page.getByRole('button',{name:'读取同步状态',exact:true}).click();await page.waitForTimeout(400)
 }
 await page.getByText('当前目标版本 1 · 已确认版本 1',{exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:'核对并恢复同步',exact:true}).count(),0)
 await page.getByRole('button',{name:'查询隔离记录',exact:true}).click();await page.getByRole('table').waitFor();assert.ok(quarantine.total>0)
 for(const item of quarantine.items)assert.deepEqual(Object.keys(item).sort(),['bodyHash','originalSize','quarantineId','reason','state','storedAt'].sort())
 assert.equal(await page.getByRole('button',{name:/重放|修改正文|跳过验签/}).count(),0)
 const anonymous=await browser.newContext(),shop=await anonymous.newPage();await shop.goto(`http://127.0.0.1:5173/products/${fixture.goodsId}`);await shop.locator('.product-detail').getByRole('heading',{name:'运营同步页面验收',exact:true}).waitFor();assert.equal(await shop.getByText('资料更新中，暂不可试算',{exact:true}).count(),0);assert.equal(await shop.getByRole('button',{name:'读取同步状态',exact:true}).count(),0)
 await mkdir(resolve(root,'target/sync'),{recursive:true});await page.screenshot({path:resolve(root,'target/sync/operator.png'),fullPage:true});await shop.screenshot({path:resolve(root,'target/sync/store.png'),fullPage:true});assert.deepEqual(errors,[])
 await writeFile(resolve(root,'target/sync/browser.txt'),'status=PASSED\nactual-Edge/operator-paused-detail/resume/pause/resume/real-background-worker-A-MQ-confirmation/confirmed-current-version/quarantine-six-metadata-fields/no-browser-replay/anonymous-confirmed-display/pageerrors=0\n')
 await anonymous.close();console.log('B-02.4 actual synchronization browser verification: PASSED')
}finally{await browser.close()}
