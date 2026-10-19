import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { chromium } from 'playwright-core'

const root = path.resolve(import.meta.dirname, '../..')
if (path.basename(root) !== 'zj-market-ux') throw Error('UX worktree required')
const accounts = JSON.parse(fs.readFileSync(path.join(root, '.local/b06/control/demo-accounts.json'), 'utf8'))
const buyer = accounts.b06buyer
if (!buyer?.loginName || !buyer?.password) throw Error('Private UX demo input invalid')
const output = path.join(root, '.local/ux03/evidence')
fs.mkdirSync(output, { recursive: true })
const origin = 'https://zj-market-ux.test:8446'
const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true,
  args: ['--host-resolver-rules=MAP zj-market-ux.test 127.0.0.1', '--no-proxy-server', '--no-sandbox'] })
try {
  const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1280, height: 900 } })
  const page = await context.newPage()
  const businessWrites = []
  page.on('request', request => {
    if (request.method() === 'POST' && /\/api\/v1\/(?:orders(?:\/[^/]+\/cancel)?|orders\/[^/]+\/payment-attempts|payments\/)/.test(new URL(request.url()).pathname))
      businessWrites.push(new URL(request.url()).pathname)
  })
  await page.goto(`${origin}/login?returnTo=/orders`)
  await page.locator('#loginName').fill(buyer.loginName)
  await page.locator('#password').fill(buyer.password)
  await page.locator('form button[type="submit"]').click()
  await page.getByRole('heading', { name: '我的订单' }).waitFor({ timeout: 30000 })
  await page.getByRole('button', { name: '刷新订单' }).waitFor()
  await page.locator('.empty, .order-card, [role="alert"]').first().waitFor({ timeout: 30000 })
  assert.equal(await page.locator('[role="alert"]').count(), 0)
  await page.screenshot({ path: path.join(output, 'live-orders-desktop.png'), fullPage: true })
  const detail = page.getByRole('link', { name: '查看订单与进度' }).first()
  if (await detail.count()) {
    await detail.click()
    await page.getByRole('heading', { name: '订单详情' }).waitFor()
    await page.locator('.order-detail').waitFor()
    await page.screenshot({ path: path.join(output, 'live-order-detail.png'), fullPage: true })
    const payment = page.getByRole('link', { name: /去模拟支付|查看付款结果/ }).first()
    if (await payment.count()) {
      await payment.click()
      await page.getByRole('heading', { name: '确认本次付款' }).waitFor()
      await page.locator('.payment-card').waitFor()
      await page.screenshot({ path: path.join(output, 'live-payment-readonly.png'), fullPage: true })
    } else {
      await page.goto(`${page.url()}/payment`)
      await page.getByRole('heading', { name: '确认本次付款' }).waitFor()
      await page.locator('.payment-card, [role="alert"]').first().waitFor()
      assert.equal(await page.locator('[role="alert"]').count(), 0)
      await page.screenshot({ path: path.join(output, 'live-payment-readonly.png'), fullPage: true })
    }
  }
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: path.join(output, 'live-mobile.png'), fullPage: true })
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
  assert.equal(businessWrites.length, 0)
  await context.close()
  console.log('UX03_LIVE_PASS login/orders/detail-if-present/payment-if-allowed/no-business-write/mobile')
} finally { await browser.close() }
