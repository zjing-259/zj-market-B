import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { chromium } from 'playwright-core'

const root = path.resolve(import.meta.dirname, '../..')
if (path.basename(root) !== 'zj-market-ux') throw Error('UX worktree required')
const accounts = JSON.parse(fs.readFileSync(path.join(root, '.local/b06/control/demo-accounts.json'), 'utf8'))
const buyer = accounts.b06buyer
const goodsId = fs.readFileSync(path.join(root, '.local/b06/control/seed-goods-id.txt'), 'utf8').trim()
if (!buyer?.loginName || !buyer?.password || !/^[A-Za-z0-9_-]{1,64}$/.test(goodsId)) throw Error('Private UX demo input invalid')
const output = path.join(root, '.local/ux02/evidence')
fs.mkdirSync(output, { recursive: true })
const origin = 'https://zj-market-ux.test:8446'
const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true,
  args: ['--host-resolver-rules=MAP zj-market-ux.test 127.0.0.1', '--no-proxy-server', '--no-sandbox'] })
try {
  const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1280, height: 900 } })
  const page = await context.newPage()
  let orderWrites = 0
  page.on('request', request => { if (request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/orders') orderWrites++ })
  await page.goto(`${origin}/login?returnTo=${encodeURIComponent(`/products/${goodsId}`)}`)
  await page.locator('#loginName').fill(buyer.loginName)
  await page.locator('#password').fill(buyer.password)
  await page.locator('form button[type="submit"]').click()
  await page.locator('.shop-detail').waitFor({ timeout: 30000 })
  await page.getByRole('region', { name: '购买操作' }).waitFor()
  assert.equal(new URL(page.url()).pathname, `/products/${goodsId}`)
  assert.match(await page.title(), /正经商城$/)
  assert.equal(orderWrites, 0)
  await page.screenshot({ path: path.join(output, 'live-product-desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: path.join(output, 'live-product-mobile.png'), fullPage: true })
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
  assert.equal(orderWrites, 0)
  await context.close()
  console.log('UX02_LIVE_PASS login/deep-product/purchase-panel/no-order-write/mobile')
} finally { await browser.close() }
