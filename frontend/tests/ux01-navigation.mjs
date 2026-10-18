import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { chromium } from 'playwright-core'
import { createServer } from 'vite'

const origin = 'http://127.0.0.1:5182'
const root = path.resolve(import.meta.dirname, '../..')
if (path.basename(root) !== 'zj-market-ux') throw Error('UX worktree required')
const output = path.join(root, '.local/ux01/evidence')
fs.mkdirSync(output, { recursive: true })
const user = { userId: 'buyer-1', loginName: 'buyer_1', displayName: '验收用户', roles: ['USER'] }
const product = { goodsId: 'sku', goodsName: '验收商品', description: '产品说明', imageUrl: null,
  originalPrice: '100.00', currency: 'CNY', saleStatus: 'ON_SALE', productVersion: '1',
  syncReady: true, availability: 'IN_STOCK' }
function respond(route, data, status = 200, code = '0000') {
  return route.fulfill({ status, contentType: 'application/json',
    body: JSON.stringify({ code, message: code, data, requestId: 'ux01-check' }) })
}
async function mock(page, roles = ['USER']) {
  let signedIn = false
  await page.route('**/api/v1/**', route => {
    const url = new URL(route.request().url())
    const endpoint = url.pathname.replace('/api/v1', '')
    if (endpoint === '/auth/refresh') return signedIn ? respond(route, { accessToken: 'token', expiresIn: 3600, user: { ...user, roles } }) : respond(route, null, 401, 'AUTH_REQUIRED')
    if (endpoint === '/auth/csrf') return respond(route, { token: 'csrf', headerName: 'X-CSRF' })
    if (endpoint === '/auth/login') { signedIn = true; return respond(route, { accessToken: 'token', expiresIn: 3600, user: { ...user, roles } }) }
    if (endpoint === '/auth/logout') { signedIn = false; return respond(route, null) }
    if (endpoint === '/products' || endpoint === '/admin/products') return respond(route, { items: [product], page: 1, size: 20, total: 1 })
    if (endpoint === '/products/sku' || endpoint === '/admin/products/sku') return respond(route, product)
    if (endpoint === '/products/sku/active-order') return respond(route, null)
    if (endpoint === '/products/sku/trial') return respond(route, { goodsId: 'sku', productVersion: '1', quotedAt: new Date().toISOString(), state: 'AVAILABLE', offer: { goodsId: 'sku', productVersion: '1', originalPrice: '100.00', payPrice: '90.00', targetCount: 3 } })
    if (endpoint === '/products/sku/joinable-teams') return respond(route, { state: 'AVAILABLE', reason: null, goodsId: 'sku', productVersion: '1', activityId: 'act', serverTime: new Date().toISOString(), items: [], activeOrderId: null, nextCursor: null, hasMore: false })
    if (endpoint === '/orders') return respond(route, { items: [], page: 1, size: 20, total: 0 })
    throw Error(`Unexpected UX-01 API: ${endpoint}`)
  })
}

const server = await createServer({ server: { host: '127.0.0.1', port: 5182, strictPort: true } })
await server.listen()
const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true, args: ['--no-sandbox', '--no-proxy-server'] })
try {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } })
  const page = await context.newPage()
  await mock(page)
  await page.goto(`${origin}/products/sku`)
  await page.getByRole('heading', { name: '验收商品' }).waitFor()
  assert.equal(await page.title(), '验收商品｜正经商城')
  await page.reload()
  await page.getByRole('heading', { name: '验收商品' }).waitFor()
  await page.getByRole('link', { name: '正经商城' }).click()
  assert.equal(new URL(page.url()).pathname, '/')
  assert.equal(await page.title(), '商城首页｜正经商城')
  await page.goBack()
  await page.getByRole('heading', { name: '验收商品' }).waitFor()
  assert.equal(new URL(page.url()).pathname, '/products/sku')
  await page.goForward()
  assert.equal(new URL(page.url()).pathname, '/')
  await page.goto(`${origin}/missing/path`)
  await page.getByRole('heading', { name: '没有找到这个页面' }).waitFor()
  assert.equal(await page.title(), '页面不存在｜正经商城')
  assert.equal(await page.locator('#password').count(), 0)
  await page.goto(`${origin}/teams/team-1`)
  assert.equal(await page.title(), '团队详情｜正经商城')
  await page.getByText('请登录后查看团队详情。').waitFor()
  await page.goto(`${origin}/orders/order-1/payment`)
  assert.equal(await page.title(), '模拟收银台｜正经商城')
  await page.getByText('请登录后查看本人收银台。').waitFor()
  await page.goto(`${origin}/login?returnTo=${encodeURIComponent('/products/sku')}`)
  await page.locator('#loginName').fill('buyer_1')
  await page.locator('#password').fill('123456789012')
  await page.locator('form button[type="submit"]').click()
  await page.getByRole('heading', { name: '验收商品' }).waitFor()
  assert.equal(new URL(page.url()).pathname, '/products/sku')
  await page.getByRole('link', { name: '账号中心' }).click()
  assert.equal(new URL(page.url()).pathname, '/account')
  await page.getByText('验收用户').waitFor()
  await page.evaluate(() => localStorage.setItem('b-payment:buyer-1:order-1', 'preserved-ux01'))
  await page.reload()
  await page.getByText('验收用户').waitFor()
  assert.equal(await page.title(), '账号中心｜正经商城')
  assert.equal(await page.evaluate(() => localStorage.getItem('b-payment:buyer-1:order-1')), 'preserved-ux01')
  await page.getByRole('button', { name: '退出登录' }).click()
  await page.waitForURL(`${origin}/login`)
  assert.equal(new URL(page.url()).pathname, '/login')
  assert.equal(await page.getByText('验收用户').count(), 0)
  await page.goto(`${origin}/admin/products`)
  assert.equal(await page.getByRole('navigation', { name: '运营导航' }).count(), 0)
  await page.getByText('请使用运营账号登录后维护商品。').waitFor()
  await page.goto(`${origin}/products`)
  await page.getByRole('heading', { name: '在售商品' }).waitFor()
  await page.screenshot({ path: path.join(output, 'desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: path.join(output, 'mobile.png'), fullPage: true })
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true)
  await context.close()

  const admin = await browser.newPage()
  await mock(admin, ['USER', 'OPERATOR'])
  await admin.goto(`${origin}/login?returnTo=/products`)
  await admin.locator('#loginName').fill('buyer_1')
  await admin.locator('#password').fill('123456789012')
  await admin.locator('form button[type="submit"]').click()
  await admin.getByRole('link', { name: '账号中心' }).waitFor()
  await admin.getByRole('link', { name: '运营工作台' }).click()
  assert.equal(new URL(admin.url()).pathname, '/admin/products')
  await admin.goto(`${origin}/admin/products`)
  await admin.getByRole('navigation', { name: '运营导航' }).waitFor()
  assert.equal(await admin.title(), '商品管理｜正经商城')
  await admin.close()
  console.log('UX01_NAVIGATION_PASS brand/title/deep-link/history/404/returnTo/logout/layout/mobile')
} finally { await browser.close(); await server.close() }
