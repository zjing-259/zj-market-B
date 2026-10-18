import assert from 'node:assert/strict'
import { test } from 'node:test'
import { chromium } from 'playwright-core'
import { createServer } from 'vite'

const edge = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
const origin = 'http://127.0.0.1:5178'
const user = { userId: 'buyer-1', loginName: 'buyer_1', displayName: '测试用户', roles: ['USER'] }
const product = goodsId => ({ goodsId, goodsName: `商品 ${goodsId}`, description: '', imageUrl: null, originalPrice: '100.00', currency: 'CNY', saleStatus: 'ON_SALE', productVersion: '1', syncReady: true, availability: 'IN_STOCK' })
const offer = goodsId => ({ activityId: 'activity-1', goodsId, productVersion: '1', originalPrice: '100.00', deductionPrice: '10.00', payPrice: '90.00', currency: 'CNY', targetCount: 3 })
const team = (teamId, count = 1) => ({ teamId, targetCount: 3, reservedCount: count, paidCount: 1, availableSlots: 3 - count, remainingPaidCount: 2, validEndTime: new Date(Date.now() + 120000).toISOString() })
const discovery = (goodsId, items, hasMore = false) => ({ state: 'AVAILABLE', reason: null, goodsId, productVersion: '1', activityId: 'activity-1', serverTime: new Date().toISOString(), items, activeOrderId: null, nextCursor: hasMore ? 'next-page' : null, hasMore })
const reply = (route, data, status = 200, code = 'SUCCESS', headers = {}) => route.fulfill({ status, contentType: 'application/json', headers, body: JSON.stringify({ code, message: code, data, requestId: 'test-request' }) })

async function mockApi(page, discover) {
  const calls = []
  let loggedIn = false
  await page.route('**/api/v1/**', async route => {
    const url = new URL(route.request().url())
    const path = url.pathname.replace('/api/v1', '')
    calls.push(path + url.search)
    if (path === '/auth/refresh') return loggedIn ? reply(route, { accessToken: 'test-token', expiresIn: 3600, user }) : reply(route, null, 401, 'AUTH_REQUIRED')
    if (path === '/auth/csrf') return reply(route, { token: 'csrf', headerName: 'X-CSRF' })
    if (path === '/auth/login') { loggedIn = true; return reply(route, { accessToken: 'test-token', expiresIn: 3600, user }) }
    if (path === '/products') return reply(route, { items: [product('sku'), product('other')], page: 1, size: 20, total: 2 })
    const goods = path.match(/^\/products\/([^/]+)$/)
    if (goods) return reply(route, product(decodeURIComponent(goods[1])))
    const trial = path.match(/^\/products\/([^/]+)\/trial$/)
    if (trial) return reply(route, { goodsId: decodeURIComponent(trial[1]), productVersion: '1', quotedAt: new Date().toISOString(), state: 'AVAILABLE', offer: offer(decodeURIComponent(trial[1])) })
    if (/^\/products\/[^/]+\/active-order$/.test(path)) return reply(route, null)
    if (path === '/purchase-confirmations') {
      const body = JSON.parse(route.request().postData() ?? '{}')
      calls.push(`confirmation:${body.teamId}:${body.mode}`)
      return reply(route, { confirmationId: 'confirmation-1', mode: body.mode, teamId: body.teamId, offer: body.expectedOffer, quantity: 1, issuedAt: new Date().toISOString(), expiresAt: new Date(Date.now() + 60000).toISOString() })
    }
    const listing = path.match(/^\/products\/([^/]+)\/joinable-teams$/)
    if (listing) return discover(route, decodeURIComponent(listing[1]), url.searchParams)
    const teamPath = path.match(/^\/teams\/([^/]+)$/)
    if (teamPath) { const id = decodeURIComponent(teamPath[1]); return reply(route, { teamId: id, goodsId: 'sku', activityId: 'activity-1', status: 'FORMING', version: '1', targetCount: 3, reservedCount: 1, paidCount: 1, validStartTime: new Date(Date.now() - 60000).toISOString(), validEndTime: new Date(Date.now() + 120000).toISOString(), serverTime: new Date().toISOString(), joinable: true, myOrderId: null }) }
    throw Error(`Unexpected API call: ${path}`)
  })
  return calls
}
async function login(page, id = 'sku') {
  await page.goto(`${origin}/login?returnTo=${encodeURIComponent(`/products/${id}`)}`)
  await page.locator('#loginName').fill('buyer_1')
  await page.locator('#password').fill('123456789012')
  await page.locator('form button[type="submit"]').click()
  await page.getByRole('heading', { name: '正在拼团' }).waitFor()
}

const vite = await createServer({ server: { host: '127.0.0.1', port: 5178, strictPort: true } })
await vite.listen()
const browser = await chromium.launch({ executablePath: edge, headless: true, args: ['--no-sandbox'] })
try {
  await test('login, pagination and the existing JOIN path keep the chosen team ID', async () => {
    const page = await browser.newPage()
    try {
      const calls = await mockApi(page, (route, goods, query) => reply(route, discovery(goods, [team(query.has('cursor') ? '团队-二' : '团队-一')], !query.has('cursor'))))
      await login(page)
      assert.equal(await page.getByText('已支付 1 人', { exact: false }).count(), 1)
      assert.equal(await page.getByText('可加入 2 位', { exact: false }).count(), 1)
      await page.getByRole('button', { name: '查看更多' }).click()
      await page.getByRole('link', { name: '去参团' }).nth(1).click()
      await page.getByRole('heading', { name: '拼团详情' }).waitFor()
      assert.match(page.url(), /%E5%9B%A2%E9%98%9F-%E4%BA%8C/)
      assert.equal(await page.getByRole('button', { name: '加入此团队' }).count(), 1)
      await page.getByRole('button', { name: '加入此团队' }).click()
      await page.getByRole('button', { name: '确认下单并去支付' }).waitFor()
      assert(calls.includes('confirmation:团队-二:JOIN'))
      assert(calls.some(path => path.includes('/joinable-teams?limit=3') && !path.includes('cursor=')))
      assert(calls.some(path => path.includes('/joinable-teams?limit=10&cursor=next-page')))
      assert(calls.some(path => path.startsWith('/teams/%E5%9B%A2%E9%98%9F-%E4%BA%8C')))
    } finally { await page.close() }
  })
  await test('stale response from previous product cannot overwrite the new product', async () => {
    const page = await browser.newPage()
    let release
    const held = new Promise(resolve => { release = resolve })
    try {
      await mockApi(page, async (route, goods) => {
        if (goods === 'sku') await held
        return reply(route, discovery(goods, [team(goods === 'sku' ? 'old-team' : 'new-team')]))
      })
      await login(page)
      await page.evaluate(() => { history.pushState(null, '', '/products/other'); window.dispatchEvent(new PopStateEvent('popstate')) })
      await page.locator('a[href="/teams/new-team"]').waitFor()
      release()
      await page.waitForTimeout(200)
      assert.equal(await page.locator('a[href="/teams/old-team"]').count(), 0)
    } finally { release(); await page.close() }
  })
  await test('rate limit observes Retry-After and does not auto-retry', async () => {
    const page = await browser.newPage()
    try {
      const calls = await mockApi(page, route => reply(route, null, 429, 'RATE_LIMITED', { 'Retry-After': '2' }))
      await login(page)
      await page.getByText(/请 \d 秒后重试/).waitFor()
      assert.equal(await page.getByRole('button', { name: '刷新待拼团队' }).isDisabled(), true)
      const count = calls.filter(path => path.includes('/joinable-teams')).length
      await page.waitForTimeout(2200)
      assert.equal(calls.filter(path => path.includes('/joinable-teams')).length, count)
    } finally { await page.close() }
  })
  await test('expired card becomes unavailable and refreshes without switching teams', async () => {
    const page = await browser.newPage()
    let reads = 0
    try {
      await mockApi(page, (route, goods) => {
        reads++
        const item = { ...team('expiring-team'), validEndTime: new Date(Date.now() + 1100).toISOString() }
        return reply(route, discovery(goods, reads === 1 ? [item] : []))
      })
      await login(page)
      await page.locator('a[href="/teams/expiring-team"]').waitFor()
      await page.getByText('暂无可参与的拼团，可以自己开团。').waitFor({ timeout: 5000 })
      assert(reads >= 2)
      assert.equal(await page.locator('a[href="/teams/expiring-team"]').count(), 0)
    } finally { await page.close() }
  })
  await test('pagination context change discards the old team list', async () => {
    const page = await browser.newPage()
    let firstPages = 0
    try {
      await mockApi(page, (route, goods, query) => {
        if (query.has('cursor')) return reply(route, null, 409, 'TEAM_DISCOVERY_CONTEXT_CHANGED')
        firstPages++
        return reply(route, discovery(goods, [team(firstPages === 1 ? 'old-team' : 'new-team')], firstPages === 1))
      })
      await login(page)
      await page.getByRole('button', { name: '查看更多' }).click()
      await page.locator('a[href="/teams/new-team"]').waitFor()
      assert.equal(await page.locator('a[href="/teams/old-team"]').count(), 0)
      assert.equal(firstPages, 2)
    } finally { await page.close() }
  })
  await test('hidden page pauses reads and the five-minute window stops auto refresh', async () => {
    const page = await browser.newPage()
    try {
      await page.clock.install()
      const calls = await mockApi(page, (route, goods) => reply(route, discovery(goods, [team('steady-team')])))
      await login(page)
      const reads = () => calls.filter(path => path.includes('/joinable-teams')).length
      const initial = reads()
      await page.evaluate(() => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => true }); document.dispatchEvent(new Event('visibilitychange')) })
      await page.clock.fastForward(20_000)
      assert.equal(reads(), initial)
      await page.evaluate(() => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => false }); document.dispatchEvent(new Event('visibilitychange')) })
      for (let i = 0; i < 30 && reads() <= initial; i++) await new Promise(resolve => setTimeout(resolve, 100))
      assert(reads() > initial)
      await page.clock.fastForward(301_000)
      await new Promise(resolve => setTimeout(resolve, 100))
      const stoppedAt = reads()
      await page.clock.fastForward(30_000)
      await new Promise(resolve => setTimeout(resolve, 100))
      assert.equal(reads(), stoppedAt)
      await page.getByRole('button', { name: '刷新待拼团队' }).click()
      for (let i = 0; i < 30 && reads() <= stoppedAt; i++) await new Promise(resolve => setTimeout(resolve, 100))
      assert(reads() > stoppedAt)
    } finally { await page.close() }
  })
} finally { await browser.close(); await vite.close() }
