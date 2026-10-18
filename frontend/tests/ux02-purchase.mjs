import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { chromium } from 'playwright-core'
import { createServer } from 'vite'

const origin = 'http://127.0.0.1:5183'
const root = path.resolve(import.meta.dirname, '../..')
if (path.basename(root) !== 'zj-market-ux') throw Error('UX worktree required')
const evidence = path.join(root, '.local/ux02/evidence')
fs.mkdirSync(evidence, { recursive: true })
const person = { userId: 'buyer-ux02', loginName: 'buyer_ux02', displayName: '购买验收', roles: ['USER'] }
const product = (availability = 'IN_STOCK') => ({ goodsId: 'sku', goodsName: '拼团验收商品', description: '适合测试的商品', imageUrl: null,
  originalPrice: '100.00', currency: 'CNY', saleStatus: 'ON_SALE', productVersion: '1', syncReady: true, availability })
const offer = (price = '90.00') => ({ activityId: 'activity-1', goodsId: 'sku', productVersion: '1', originalPrice: '100.00',
  deductionPrice: price === '90.00' ? '10.00' : '9.00', payPrice: price, currency: 'CNY', targetCount: 3 })
const order = (paymentEnabled = false) => ({ orderId: 'order-1', purchaseIntentId: 'intent-1', confirmationId: 'confirmation-1',
  status: paymentEnabled ? 'WAITING_PAYMENT' : 'PROCESSING', paymentEnabled, mode: 'OPEN', teamId: null })
function reply(route, data, status = 200, code = '0000') {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify({ code, message: code, data, requestId: 'ux02-request' }) })
}
async function setup(page, options = {}) {
  const state = { loggedIn: false, confirmations: [], writes: [], reads: 0, quotePrice: '90.00', changed: false }
  await page.route('**/api/v1/**', async route => {
    const url = new URL(route.request().url())
    const endpoint = url.pathname.replace('/api/v1', '')
    if (endpoint === '/auth/refresh') return state.loggedIn ? reply(route, { accessToken: 'token', expiresIn: 3600, user: person }) : reply(route, null, 401, 'AUTH_REQUIRED')
    if (endpoint === '/auth/csrf') return reply(route, { token: 'csrf', headerName: 'X-CSRF' })
    if (endpoint === '/auth/login') { state.loggedIn = true; return reply(route, { accessToken: 'token', expiresIn: 3600, user: person }) }
    if (endpoint === '/products') return reply(route, { items: [product(options.availability)], page: 1, size: 20, total: 1 })
    if (endpoint === '/products/sku') return reply(route, product(options.availability))
    if (endpoint === '/products/sku/trial') return reply(route, { goodsId: 'sku', productVersion: '1', quotedAt: new Date().toISOString(),
      state: options.noOffer ? 'NO_PUBLIC_OFFER' : 'AVAILABLE', offer: options.noOffer ? null : offer(state.quotePrice) })
    if (endpoint === '/products/sku/active-order') return options.activeOrder ? reply(route, order(false)) : options.lookupFailure ? reply(route, null, 503, 'DEPENDENCY_UNAVAILABLE') : reply(route, null)
    if (endpoint === '/products/sku/joinable-teams') return reply(route, { state: options.noOffer ? 'UNAVAILABLE' : 'AVAILABLE',
      reason: options.noOffer ? 'NO_OFFER' : null, goodsId: 'sku', productVersion: '1', activityId: 'activity-1',
      serverTime: new Date().toISOString(), items: [], activeOrderId: null, nextCursor: null, hasMore: false })
    if (endpoint === '/teams/team-1') return reply(route, { teamId: 'team-1', goodsId: 'sku', activityId: 'activity-1', status: 'FORMING',
      version: '1', targetCount: 3, reservedCount: 2, paidCount: 1, validStartTime: new Date().toISOString(),
      validEndTime: new Date(Date.now() + 300000).toISOString(), serverTime: new Date().toISOString(), joinable: true, myOrderId: null })
    if (endpoint === '/purchase-confirmations') {
      const body = JSON.parse(route.request().postData() ?? '{}')
      state.confirmations.push(body)
      if (options.delayedConfirmation) await new Promise(resolve => { state.releaseConfirmation = resolve })
      if (options.changeOffer && !state.changed) { state.changed = true; state.quotePrice = '91.00'; return reply(route, { latestOffer: offer('91.00') }, 409, 'OFFER_CHANGED') }
      return reply(route, { confirmationId: 'confirmation-1', mode: body.mode, teamId: body.teamId ?? null,
        offer: options.confirmationDrift ? offer('91.00') : body.expectedOffer, quantity: 1, issuedAt: new Date().toISOString(), expiresAt: new Date(Date.now() + 60000).toISOString() })
    }
    if (endpoint === '/orders' && route.request().method() === 'POST') {
      state.writes.push(JSON.parse(route.request().postData() ?? '{}'))
      if (options.unknown && state.writes.length === 1) return route.abort('failed')
      return reply(route, order(false), 202)
    }
    if (endpoint === '/orders/by-intent/' + (state.writes[0]?.purchaseIntentId ?? 'missing')) return reply(route, null, 404, 'ORDER_NOT_FOUND')
    if (endpoint === '/orders/order-1') { state.reads++; return reply(route, order(state.reads >= 2)) }
    throw Error(`Unexpected UX-02 API: ${endpoint}`)
  })
  return state
}
async function login(page, target = '/products/sku') {
  await page.goto(`${origin}/login?returnTo=${encodeURIComponent(target)}`)
  await page.locator('#loginName').fill('buyer_ux02')
  await page.locator('#password').fill('123456789012')
  await page.locator('form button[type="submit"]').click()
}
const server = await createServer({ server: { host: '127.0.0.1', port: 5183, strictPort: true } })
await server.listen()
const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true, args: ['--no-sandbox', '--no-proxy-server'] })
try {
  {
    const page = await browser.newPage()
    const state = await setup(page)
    await login(page)
    await page.getByRole('button', { name: '单独开团' }).waitFor()
    await page.screenshot({ path: path.join(evidence, 'product-desktop.png'), fullPage: true })
    assert.equal(state.writes.length, 0)
    await page.getByRole('button', { name: '单独开团' }).click()
    await page.getByRole('heading', { name: '确认本次购买' }).waitFor()
    assert.equal(state.writes.length, 0)
    await page.getByRole('button', { name: '确认下单并去支付' }).click()
    await page.getByText('订单正在确认').waitFor()
    assert.equal(await page.getByRole('link', { name: '查看订单并去支付' }).count(), 0)
    await page.getByRole('link', { name: '查看订单并去支付' }).waitFor({ timeout: 10000 })
    assert.equal(state.writes.length, 1)
    await page.close()
  }
  {
    const page = await browser.newPage()
    const state = await setup(page)
    await login(page, '/teams/team-1')
    await page.getByRole('button', { name: '加入此团队' }).waitFor()
    await page.setViewportSize({ width: 390, height: 844 })
    await page.screenshot({ path: path.join(evidence, 'team-mobile.png'), fullPage: true })
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    await page.getByRole('button', { name: '加入此团队' }).click()
    await page.getByRole('heading', { name: '确认本次购买' }).waitFor()
    assert.equal(state.confirmations[0].mode, 'JOIN')
    assert.equal(state.confirmations[0].teamId, 'team-1')
    assert.equal(state.writes.length, 0)
    await page.evaluate(() => Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: () => Promise.reject(Error('denied')) } }))
    await page.getByRole('button', { name: '复制邀请链接' }).click()
    await page.getByText('无法自动复制，请选择下方地址手动复制。').waitFor()
    assert.equal(await page.locator('#shareLink').inputValue(), `${origin}/teams/team-1`)
    await page.close()
  }
  {
    const page = await browser.newPage()
    const state = await setup(page, { changeOffer: true })
    await login(page)
    await page.getByRole('button', { name: '单独开团' }).click()
    await page.getByText('当前可能的实付价为 ¥ 91.00').waitFor()
    assert.equal(await page.getByRole('button', { name: '确认下单并去支付' }).count(), 0)
    assert.equal(state.writes.length, 0)
    await page.getByRole('button', { name: '重新读取优惠' }).last().click()
    await page.getByText('拼团实付 ¥ 91.00').waitFor()
    await page.getByRole('button', { name: '单独开团' }).click()
    await page.getByRole('heading', { name: '确认本次购买' }).waitFor()
    assert.equal(state.confirmations.length, 2)
    await page.close()
  }
  {
    const page = await browser.newPage()
    const state = await setup(page, { unknown: true })
    await login(page)
    await page.getByRole('button', { name: '单独开团' }).click()
    await page.getByRole('button', { name: '确认下单并去支付' }).click()
    await page.getByText('购买结果待核对').waitFor()
    assert.equal(state.writes.length, 1)
    const pending = await page.evaluate(() => localStorage.getItem('b-purchase:buyer-ux02:sku'))
    assert(pending?.includes(state.writes[0].purchaseIntentId))
    await page.reload()
    await page.getByText('购买结果待核对').waitFor()
    assert.equal(state.writes.length, 1)
    await page.waitForTimeout(3200)
    assert.equal(state.writes.length, 1)
    await page.getByRole('button', { name: '用原编号重试' }).click()
    await page.getByText('订单正在确认').waitFor()
    assert.equal(state.writes.length, 2)
    assert.equal(state.writes[1].purchaseIntentId, state.writes[0].purchaseIntentId)
    await page.close()
  }
  {
    const page = await browser.newPage()
    const state = await setup(page, { confirmationDrift: true })
    await login(page)
    await page.getByRole('button', { name: '单独开团' }).click()
    await page.getByText('购买条件已经变化，请重新读取优惠后再次确认。').waitFor()
    assert.equal(await page.getByRole('button', { name: '确认下单并去支付' }).count(), 0)
    assert.equal(state.writes.length, 0)
    await page.close()
  }
  {
    const page = await browser.newPage()
    const state = await setup(page, { delayedConfirmation: true })
    await login(page)
    await page.getByRole('button', { name: '单独开团' }).click()
    for (let attempt = 0; attempt < 40 && !state.releaseConfirmation; attempt++) await page.waitForTimeout(50)
    assert(state.releaseConfirmation)
    state.quotePrice = '91.00'
    await page.getByRole('button', { name: '重新读取优惠' }).first().click()
    await page.getByText('拼团实付 ¥ 91.00').waitFor()
    state.releaseConfirmation()
    await page.waitForTimeout(200)
    assert.equal(await page.getByRole('button', { name: '确认下单并去支付' }).count(), 0)
    assert.equal(state.writes.length, 0)
    await page.close()
  }
  for (const options of [{ noOffer: true }, { availability: 'OUT_OF_STOCK' }]) {
    const page = await browser.newPage()
    const state = await setup(page, options)
    await login(page)
    await page.getByRole('heading', { name: '拼团验收商品' }).waitFor()
    await page.waitForTimeout(500)
    assert.equal(await page.getByRole('button', { name: '单独开团' }).count(), 0)
    assert.equal(state.writes.length, 0)
    await page.close()
  }
  for (const options of [{ activeOrder: true }, { lookupFailure: true }]) {
    const page = await browser.newPage()
    const state = await setup(page, options)
    await login(page)
    if (options.activeOrder) await page.getByRole('link', { name: '查看原订单' }).waitFor()
    else await page.getByText(/服务暂时不可用/).first().waitFor()
    assert.equal(state.writes.length, 0)
    await page.close()
  }
  console.log('UX02_PURCHASE_PASS open/join/fixed-team/price-change/unknown/stock/no-offer/share')
} finally { await browser.close(); await server.close() }
