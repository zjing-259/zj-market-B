import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { chromium } from 'playwright-core'
const root = path.resolve(import.meta.dirname, '../..')
if (path.basename(root) !== 'zj-market-ux') throw Error('UX worktree required')
const accounts = JSON.parse(fs.readFileSync(path.join(root, '.local/b06/control/demo-accounts.json'), 'utf8'))
const fixture = JSON.parse(fs.readFileSync(path.join(root, '.local/ux04/demo-fixture.json'), 'utf8'))
const output = path.join(root, '.local/ux04/evidence')
fs.mkdirSync(output, { recursive: true })
const origin = 'https://zj-market-ux.test:8446'
const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true,
  args: ['--host-resolver-rules=MAP zj-market-ux.test 127.0.0.1', '--no-proxy-server', '--no-sandbox'] })
let businessWrites = 0
async function person(key, target) {
  const context = await browser.newContext({ ignoreHTTPSErrors: false, viewport: { width: 1440, height: 1000 } })
  const page = await context.newPage()
  let token
  page.on('response', async response => {
    if (response.url().endsWith('/auth/login') && response.status() === 200) token = (await response.json()).data.accessToken
  })
  page.on('request', request => {
    if (['POST', 'PUT', 'DELETE'].includes(request.method()) && /\/api\/v1\/(?:admin\/|orders|payments\/)/.test(new URL(request.url()).pathname)) businessWrites++
  })
  await page.goto(origin + '/login')
  assert(await page.evaluate(() => isSecureContext && !!navigator.locks))
  await page.getByLabel('登录名').fill(accounts[key].loginName)
  await page.getByLabel('密码', { exact: true }).fill(accounts[key].password)
  await page.locator('form button[type="submit"]').click()
  await page.waitForURL(url => url.pathname !== '/login')
  await page.goto(origin + target)
  return { context, page, token: () => token }
}
try {
  const operator = await person('b06operator', '/admin/products')
  const page = operator.page
  await page.getByRole('navigation', { name: '运营导航', exact: true }).waitFor()
  for (const item of fixture.items) await page.getByRole('heading', { name: item.name, exact: true }).waitFor()
  await page.screenshot({ path: path.join(output, 'live-products-1440.png'), fullPage: true })
  await page.goto(origin + '/admin/inventory')
  await page.getByRole('textbox', { name: '按商品编号查询' }).fill(fixture.items[0].goodsId)
  const filtered = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/admin/inventory' && new URL(response.url()).searchParams.get('goodsId') === fixture.items[0].goodsId)
  await page.getByRole('button', { name: '查询库存', exact: true }).click()
  await filtered
  await page.getByRole('row').filter({ hasText: fixture.items[0].goodsId }).getByRole('button', { name: '维护库存' }).click()
  await page.getByRole('heading', { name: '维护当前商品库存' }).waitFor()
  for (const width of [360, 390, 1280, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    await page.screenshot({ path: path.join(output, 'live-inventory-' + width + '.png'), fullPage: true })
  }
  const buyer = await person('b06buyer', '/products/' + fixture.items[0].goodsId)
  const productPage = buyer.page
  await productPage.getByText('拼团实付 ¥ 89.00').waitFor()
  await productPage.getByText('暂无可参与的拼团，可以自己开团。', { exact: true }).waitFor()
  assert.equal(await productPage.getByRole('alert').count(), 0)
  const picture = productPage.locator('.product-media img')
  await picture.waitFor()
  await productPage.waitForFunction(() => document.querySelector('.product-media img')?.naturalWidth > 0)
  assert.equal(await productPage.getByRole('navigation', { name: '运营导航', exact: true }).count(), 0)
  const status = await productPage.evaluate(async token => (await fetch('/api/v1/admin/inventory?page=1&size=20',
    { headers: { Authorization: 'Bearer ' + token } })).status, buyer.token())
  assert.equal(status, 403)
  await productPage.screenshot({ path: path.join(output, 'live-cup-1440.png'), fullPage: true })
  await productPage.setViewportSize({ width: 360, height: 844 })
  assert(await productPage.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
  await productPage.screenshot({ path: path.join(output, 'live-cup-360.png'), fullPage: true })
  await productPage.goto(origin + '/products/' + fixture.items[1].goodsId)
  await productPage.getByText('拼团实付 ¥ 49.00').waitFor()
  await productPage.getByText('暂无可参与的拼团，可以自己开团。', { exact: true }).waitFor()
  assert.equal(await productPage.getByRole('alert').count(), 0)
  await productPage.waitForFunction(() => document.querySelector('.product-media img')?.naturalWidth > 0)
  assert.equal(businessWrites, 0)
  await buyer.context.close(); await operator.context.close()
  console.log('UX04_LIVE_PASS trusted-browser-TLS/operator/buyer-403/two-products/local-images/360-390-1280-1440/no-business-write')
} finally { await browser.close() }
