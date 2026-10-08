import {createRequire} from 'node:module'
import {resolve,dirname} from 'node:path'
import {fileURLToPath} from 'node:url'
import {mkdir,writeFile} from 'node:fs/promises'
import {randomUUID} from 'node:crypto'
import assert from 'node:assert/strict'
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..')
const {chromium}=createRequire(resolve(root,'target/b02-browser-runtime/package.json'))('playwright')
const browser=await chromium.launch({headless:true,executablePath:process.env.B_BROWSER_EXECUTABLE??'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'})
const context=await browser.newContext({viewport:{width:1280,height:1000}}),page=await context.newPage(),errors=[]
page.on('pageerror',e=>errors.push(e.message))
const name='浏览器商品'+randomUUID().slice(0,8)
let created,accessToken;const writes=[]
page.on('response',async response=>{
 if(response.url().endsWith('/auth/login')&&response.status()===200)accessToken=(await response.json()).data.accessToken
 if(response.request().method()==='POST'&&response.url().endsWith('/admin/products')&&response.status()===201)created=(await response.json()).data
 if(['POST','PUT'].includes(response.request().method())&&response.url().includes('/admin/products'))writes.push(response.status())
})
try{
 await page.goto('http://127.0.0.1:5173/products');await page.getByRole('heading',{name:'在售商品',exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:'商品管理',exact:true}).count(),0)
 await page.getByRole('button',{name:'账号中心',exact:true}).click();await page.locator('#loginName').fill(process.env.B_BROWSER_OPERATOR_LOGIN_NAME);await page.locator('#password').fill(process.env.B_BROWSER_OPERATOR_PASSWORD)
 await page.getByRole('button',{name:'登录',exact:true}).last().click();await page.getByRole('button',{name:'商品管理',exact:true}).waitFor();await page.getByRole('button',{name:'商品管理',exact:true}).click()
 await page.getByRole('button',{name:'创建商品',exact:true}).click();await page.locator('#goodsName').fill('  '+name+'  ');await page.locator('#description').fill('原文\n  描述保留空白');await page.locator('#originalPrice').fill('88.50')
 const hint=page.locator('#goodsNameHint');await hint.waitFor();assert.match(await hint.textContent(),/128.*UTF-16/)
 const beforeInvalid=writes.length;await page.locator('#goodsName').fill('🛍'.repeat(65));await page.getByRole('button',{name:'保存商品',exact:true}).click();await page.getByRole('alert').filter({hasText:'1～128 个 UTF-16 单元'}).waitFor();assert.equal(writes.length,beforeInvalid)
 await page.locator('#goodsName').fill('  '+name+'  ')
 await page.getByRole('button',{name:'保存商品',exact:true}).click();await page.getByRole('heading',{name,exact:true}).waitFor();assert.equal(created.productVersion,'1');assert.equal(created.saleStatus,'OFF_SALE')
 const anonymous=await browser.newContext(),shop=await anonymous.newPage();await shop.goto(`http://127.0.0.1:5173/products/${created.goodsId}`);await shop.getByRole('alert').filter({hasText:'商品不存在或已下架'}).waitFor()
 await page.getByRole('button',{name:'编辑商品',exact:true}).click();await page.locator('#saleStatus').selectOption('ON_SALE');await page.getByRole('button',{name:'保存商品',exact:true}).click();await page.getByText('在售 · 商品版本 2',{exact:true}).waitFor()
 await shop.reload();await shop.getByRole('heading',{name,exact:true}).waitFor();await shop.getByText('资料更新中，暂不可试算',{exact:true}).waitFor();assert.equal(await shop.getByRole('button',{name:/购买|支付|下单/}).count(),0)
 await page.getByRole('button',{name:'编辑商品',exact:true}).click();await page.getByRole('button',{name:'保存商品',exact:true}).click();await page.getByText('内容没有变化，版本保持不变。',{exact:true}).waitFor();await page.getByText('在售 · 商品版本 2',{exact:true}).waitFor()
 // An external editor wins while the browser still edits version 2. No mutation retry.
 await page.getByRole('button',{name:'编辑商品',exact:true}).click()
 const remote=await page.evaluate(async({id,jwt})=>{
  const headers={Authorization:`Bearer ${jwt}`,'Content-Type':'application/json'}
  const before=(await(await fetch(`/api/v1/admin/products/${id}`,{headers})).json()).data
  return (await(await fetch(`/api/v1/admin/products/${id}`,{method:'PUT',headers,body:JSON.stringify({goodsName:before.goodsName,description:'另一位编辑者的资料',imageUrl:null,originalPrice:before.originalPrice,currency:'CNY',saleStatus:before.saleStatus,expectedVersion:before.productVersion})})).json()).data
 },{id:created.goodsId,jwt:accessToken});assert.equal(remote.productVersion,'3')
 const countBefore=writes.length;await page.locator('#description').fill('冲突修改');await page.getByRole('button',{name:'保存商品',exact:true}).click();await page.getByRole('alert').filter({hasText:'商品已被其他人修改'}).waitFor();await page.waitForTimeout(300);assert.deepEqual(writes.slice(countBefore),[409])
 await page.getByRole('button',{name:'重新读取',exact:true}).click();await page.getByText('当前编辑版本：3',{exact:true}).waitFor();assert.equal(await page.locator('#description').inputValue(),'另一位编辑者的资料')
 await page.locator('#description').fill('<b>不应保存HTML</b>');await page.getByRole('button',{name:'保存商品',exact:true}).click();await page.getByRole('alert').filter({hasText:'请检查填写内容'}).waitFor()
 await page.locator('#description').fill('原文\n  描述保留空白');await page.locator('#imageUrl').fill('https://example.invalid/missing.png');await page.getByRole('button',{name:'保存商品',exact:true}).click();await page.getByText('在售 · 商品版本 4',{exact:true}).waitFor();await page.getByText('商品图片暂无',{exact:true}).waitFor()
 await shop.reload();await shop.getByRole('heading',{name,exact:true}).waitFor();assert.equal(await shop.locator('.product-description').textContent(),'原文\n  描述保留空白')
 await mkdir(resolve(root,'target/products'),{recursive:true});await shop.screenshot({path:resolve(root,'target/products/store.png'),fullPage:true});await page.screenshot({path:resolve(root,'target/products/operator.png'),fullPage:true})
 await page.getByRole('button',{name:'编辑商品',exact:true}).click();await page.locator('#saleStatus').selectOption('OFF_SALE');await page.getByRole('button',{name:'保存商品',exact:true}).click();await page.getByText('已下架 · 商品版本 5',{exact:true}).waitFor();await shop.reload();await shop.getByRole('alert').filter({hasText:'商品不存在或已下架'}).waitFor()
 assert.deepEqual(errors,[]);await anonymous.close();await writeFile(resolve(root,'target/products/browser.txt'),'status=PASSED\nEdge real browser: anonymous/public detail, operator create/edit/up/down, UTF16 name hint/emoji-overflow-blocked, no-op version, conflict no automatic replay, explicit reread, HTML rejection, image fallback, preserved description, pending sync, no purchase flow; pageerrors=0\n')
 console.log('B-02.3 actual product browser verification: PASSED')
}finally{await browser.close()}
