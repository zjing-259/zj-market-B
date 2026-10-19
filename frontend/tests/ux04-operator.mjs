import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { chromium } from 'playwright-core'
import { createServer } from 'vite'
const origin = 'http://127.0.0.1:5185'
const root = path.resolve(import.meta.dirname, '../..')
if (path.basename(root) !== 'zj-market-ux') throw Error('UX worktree required')
const output = path.join(root, '.local/ux04/evidence')
fs.mkdirSync(output, { recursive: true })
const respond = (route, data, status = 200, code = '0000') => route.fulfill({ status, contentType: 'application/json',
  body: JSON.stringify({ code, message: code, data, requestId: 'ux04-check' }) })
async function mock(context, options = {}) {
  const person = { userId: 'operator-ux04', loginName: 'operator_ux04', displayName: '运营验收', roles: options.buyer ? ['USER'] : ['USER', 'OPERATOR'] }
  const state = { signedIn: false, stock: '10', version: '1', inventoryWrites: [], productWrites: [], controls: [], failedProduct: false }
  const product = () => ({ goodsId: 'sku', goodsName: '轻行随身杯', description: '原创插画商品说明', imageUrl: origin + '/demo/ux04-cup.svg',
    originalPrice: '99.00', currency: 'CNY', saleStatus: 'ON_SALE', productVersion: state.failedProduct ? '2' : '1',
    syncReady: true, availability: 'IN_STOCK', sync: { state: 'CONFIRMED', targetVersion: '1', confirmedVersion: '1', targetEventId: 'event-1' } })
  const stock = () => ({ goodsId: 'sku', available: state.stock, reserved: '1', sold: '2', version: state.version, updatedAt: new Date().toISOString() })
  const coordination = () => ({ orderId: 'order-1', version: '7', intent: 'RESERVE', runState: 'WAITING_DEPENDENCY', paused: false,
    consecutiveFailures: 2, alerted: true, nextAttemptAt: null, leaseUntil: null, errorCode: 'DEPENDENCY_UNAVAILABLE',
    allowedActions: ['CHECK'], recentAttempts: [{ requestId: 'a'.repeat(64), intent: 'RESERVE', startedAt: new Date().toISOString(), code: 'UPSTREAM_TIMEOUT', message: '等待依赖恢复' }] })
  const refund = { refundId: 'refund-1', orderId: 'order-1', paymentId: 'pay-1', refundAmount: '89.00', currency: 'CNY',
    fundsStatus: 'SUCCEEDED', syncStatus: 'WAITING_DEPENDENCY', releaseStatus: 'READY', version: '3', refundedAt: new Date().toISOString(),
    eligibilityStatus: 'ELIGIBLE', attemptId: 'a'.repeat(64), attemptStatus: 'SUCCEEDED', failureCode: null, failureCount: 0,
    nextAttemptAt: null, alerted: false, reasons: ['等待同步确认'], evidenceIds: ['e'.repeat(64)], allowedActions: [] }
  await context.route('**/api/v1/**', async route => {
    const endpoint = new URL(route.request().url()).pathname.replace('/api/v1', '')
    const method = route.request().method()
    if (endpoint === '/auth/refresh') return state.signedIn ? respond(route, { accessToken: 'token', expiresIn: 3600, user: person }) : respond(route, null, 401, 'AUTH_REQUIRED')
    if (endpoint === '/auth/csrf') return respond(route, { token: 'csrf', headerName: 'X-CSRF' })
    if (endpoint === '/auth/login') { state.signedIn = true; return respond(route, { accessToken: 'token', expiresIn: 3600, user: person }) }
    if (options.buyer && endpoint.startsWith('/admin/')) return respond(route, null, 403, 'FORBIDDEN')
    if (endpoint === '/admin/products' && method === 'GET') return options.listFailure ? respond(route, null, 503, 'DEPENDENCY_UNAVAILABLE')
      : respond(route, { items: [product()], page: 1, size: 20, total: 1 })
    if (endpoint === '/admin/products/sku' && method === 'GET') return respond(route, product())
    if (endpoint === '/admin/products/sku' && method === 'PUT') {
      state.productWrites.push(JSON.parse(route.request().postData()))
      if (!state.failedProduct) { state.failedProduct = true; return respond(route, null, 409, 'PRODUCT_EDIT_CONFLICT') }
      return respond(route, product())
    }
    if (endpoint === '/admin/inventory' && method === 'GET') return respond(route, { items: [stock()], page: 1, size: 20, total: 1 })
    if (endpoint === '/admin/inventory/sku' && method === 'GET') return respond(route, stock())
    if (endpoint === '/admin/inventory/sku/ledger') return respond(route, { items: [{ ledgerId: 'ledger-1', actorId: 'u'.repeat(64),
      createdAt: new Date().toISOString(), kind: 'INBOUND', delta: { available: '10' }, before: { available: '0' }, after: { available: '10' }, reason: '初始备货原因'.repeat(15) }], page: 1, size: 20, total: 1 })
    if (endpoint.startsWith('/admin/inventory/operations/')) return respond(route, null, 404, 'INVENTORY_OPERATION_NOT_FOUND')
    if (endpoint === '/admin/inventory/sku/inbounds') {
      const body = JSON.parse(route.request().postData()); state.inventoryWrites.push(body)
      if (state.inventoryWrites.length === 1) return route.abort('failed')
      state.stock = '15'; state.version = '2'
      return respond(route, { operationId: body.operationId, outcome: 'SUCCEEDED', code: '0000', message: '',
        request: { kind: 'INBOUND', goodsId: 'sku', delta: body.quantity, expectedVersion: body.expectedVersion, reason: body.reason },
        completedAt: new Date().toISOString(), inventory: stock() })
    }
    if (endpoint === '/admin/orders/exceptions') return respond(route, { items: [{ orderId: 'order-1', goodsId: 'sku', status: 'PROCESSING', reviewRequired: false, coordination: coordination() }], page: 1, size: 20, total: 1 })
    if (endpoint === '/admin/orders/order-1/coordination') return respond(route, coordination())
    if (endpoint === '/admin/orders/order-1/coordination-controls') {
      const body = JSON.parse(route.request().postData()); state.controls.push(body)
      if (state.controls.length === 1) return route.abort('failed')
      return respond(route, { operationId: body.operationId, coordination: coordination() })
    }
    if (endpoint === '/admin/refund-exceptions') return respond(route, { items: [refund], page: 0, size: 20, total: 1 })
    if (endpoint === '/admin/refunds/refund-1') return respond(route, refund)
    if (endpoint === '/admin/reconciliations') return respond(route, { items: [{ taskId: 'task-1', teamId: 't'.repeat(64), state: 'COLLECTING',
      memberCount: 2, readyCount: 1, alerted: false }], page: 0, size: 20, total: 1 })
    throw Error('Unexpected UX04 endpoint: ' + endpoint)
  })
  return state
}
async function login(page, target = '/admin/products') {
  await page.goto(origin + '/login?returnTo=' + encodeURIComponent(target))
  await page.locator('#loginName').fill('operator_ux04')
  await page.locator('#password').fill('123456789012')
  await page.locator('form button[type="submit"]').click()
  await page.waitForURL(url => url.pathname !== '/login')
  await page.goto(origin + target)
}
async function noOverflow(page) { assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'page overflow: ' + page.url()) }
const server = await createServer({ server: { host: '127.0.0.1', port: 5185, strictPort: true } })
await server.listen()
const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true, args: ['--no-sandbox', '--no-proxy-server'] })
try {
  {
    const context = await browser.newContext(), page = await context.newPage()
    const state = await mock(context)
    await login(page, '/admin/products/sku')
    await page.getByRole('button', { name: '编辑商品', exact: true }).click()
    await page.getByLabel('原价（元）').fill('109.00')
    await page.getByRole('button', { name: '保存商品', exact: true }).focus()
    await page.keyboard.press('Enter')
    await page.getByRole('alert').waitFor()
    assert.equal(state.productWrites.length, 1)
    await page.getByRole('button', { name: '重新读取', exact: true }).click()
    await page.getByText('当前编辑版本：2').waitFor()
    await page.getByRole('button', { name: '保存商品', exact: true }).click()
    await page.getByRole('button', { name: '编辑商品', exact: true }).waitFor()
    assert.equal(state.productWrites[1].expectedVersion, '2')
    await context.close()
  }
  {
    const context = await browser.newContext(), page = await context.newPage()
    const state = await mock(context)
    await login(page, '/admin/inventory')
    await page.getByRole('button', { name: '维护库存' }).click()
    await page.getByRole('heading', { name: '维护当前商品库存' }).waitFor()
    await page.getByRole('textbox', { name: '入库数量' }).fill('5')
    await page.getByRole('textbox', { name: '原因', exact: true }).fill('盘点验收')
    await page.getByRole('textbox', { name: '原因', exact: true }).press('Enter')
    await page.getByRole('heading', { name: '待核对操作' }).waitFor()
    await page.getByRole('alert').waitFor()
    assert.equal(state.inventoryWrites.length, 1)
    await page.reload()
    await page.getByRole('heading', { name: '待核对操作' }).waitFor()
    assert.equal(state.inventoryWrites.length, 1)
    await page.getByRole('button', { name: '重试原操作', exact: true }).click()
    await page.getByText(/库存操作已完成/).waitFor()
    assert.equal(state.inventoryWrites.length, 2)
    assert.equal(state.inventoryWrites[0].operationId, state.inventoryWrites[1].operationId)
    await context.close()
  }
  {
    const context = await browser.newContext(), page = await context.newPage()
    const state = await mock(context)
    await login(page, '/admin/orders/order-1')
    await page.getByRole('textbox', { name: '操作原因' }).fill('核验配置后查询原任务')
    await page.getByRole('button', { name: '立即核对', exact: true }).click()
    await page.getByText(/控制结果待核对/).waitFor()
    await page.getByRole('button', { name: '重试原控制', exact: true }).click()
    await page.getByText('原任务控制已受理，请刷新查看当前进度。').waitFor()
    assert.equal(state.controls[0].operationId, state.controls[1].operationId)
    assert.equal(state.controls[0].expectedVersion, '7')
    await context.close()
  }
  {
    const context = await browser.newContext(), page = await context.newPage()
    await mock(context)
    await login(page, '/admin/refunds/refund-1')
    await page.getByText('退款资格').waitFor()
    assert.equal(await page.getByRole('button', { name: '查询原退款' }).count(), 0)
    assert.equal(await page.getByRole('button', { name: '重试明确失败的退款' }).count(), 0)
    await context.close()
  }
  {
    const context = await browser.newContext(), page = await context.newPage()
    await mock(context, { listFailure: true })
    await login(page)
    await page.getByRole('alert').waitFor()
    assert.equal(await page.getByText('暂无商品，点击创建商品开始维护。').count(), 0)
    await context.close()
  }
  {
    const context = await browser.newContext(), page = await context.newPage()
    await mock(context, { buyer: true })
    await login(page)
    await page.getByText('请使用运营账号登录后维护商品。').waitFor()
    assert.equal(await page.getByRole('navigation', { name: '运营导航', exact: true }).count(), 0)
    await context.close()
  }
  {
    const context = await browser.newContext(), page = await context.newPage()
    await mock(context)
    await login(page)
    const pages = ['/admin/products', '/admin/products/sku', '/admin/inventory', '/admin/orders', '/admin/orders/order-1', '/admin/refunds', '/admin/refunds/refund-1', '/admin/reconciliations']
    for (const width of [360, 390, 1280, 1440]) {
      await page.setViewportSize({ width, height: 900 })
      for (const route of pages) {
        await page.goto(origin + route)
        await page.getByRole('navigation', { name: '运营导航', exact: true }).waitFor()
        await page.waitForTimeout(140)
        await noOverflow(page)
      }
      await page.goto(origin + '/admin/inventory')
      await page.getByRole('button', { name: '维护库存' }).click()
      await page.screenshot({ path: path.join(output, 'inventory-' + width + '.png'), fullPage: true })
    }
    await page.setViewportSize({ width: 1280, height: 900 })
    await page.goto(origin + '/admin/inventory')
    await page.getByRole('button', { name: '维护库存' }).waitFor()
    await page.evaluate(() => { document.body.style.zoom = '2' })
    await noOverflow(page)
    await page.screenshot({ path: path.join(output, 'inventory-zoom200.png'), fullPage: true })
    await page.evaluate(() => { document.body.style.zoom = '1' })
    await page.reload()
    await page.getByRole('button', { name: '维护库存' }).waitFor()
    await page.keyboard.press('Tab')
    assert.equal(await page.locator(':focus').textContent(), '跳到主要内容')
    await page.keyboard.press('Enter')
    assert.equal(await page.locator(':focus').getAttribute('id'), 'page-content')
    const table = page.getByRole('region', { name: '库存余额，可横向滚动' })
    await table.focus()
    assert.equal(await table.evaluate(node => getComputedStyle(node).outlineStyle), 'solid')
    for (const button of await page.getByRole('button').all()) {
      if (await button.isVisible()) assert((await button.boundingBox()).height >= 44)
    }
    const colors = await page.evaluate(() => {
      const style = getComputedStyle(document.documentElement)
      return ['--text', '--muted', '--blue', '--focus'].map(name => style.getPropertyValue(name).trim())
    })
    const luminance = hex => {
      const rgb = hex.replace('#', '').match(/../g).map(value => parseInt(value, 16) / 255).map(value => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4)
      return rgb[0] * 0.2126 + rgb[1] * 0.7152 + rgb[2] * 0.0722
    }
    for (const [index, value] of colors.entries()) assert(1.05 / (luminance(value) + 0.05) >= (index === 3 ? 3 : 4.5))
    await context.close()
  }
  console.log('UX04_OPERATOR_PASS product-conflict/stock-unknown-original-key/control-audit/capabilities/roles/360-390-1280-1440/zoom200/keyboard/contrast')
} finally { await browser.close(); await server.close() }
