import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { chromium } from 'playwright-core'
import { createServer } from 'vite'

const origin = 'http://127.0.0.1:5184'
const root = path.resolve(import.meta.dirname, '../..')
if (path.basename(root) !== 'zj-market-ux') throw Error('UX worktree required')
const evidence = path.join(root, '.local/ux03/evidence')
fs.mkdirSync(evidence, { recursive: true })
const person = { userId: 'buyer-ux03', loginName: 'buyer_ux03', displayName: '支付验收', roles: ['USER'] }
const offer = { activityId: 'act', goodsId: 'sku', productVersion: '1', originalPrice: '100.00',
  deductionPrice: '10.00', payPrice: '90.00', targetCount: 2, currency: 'CNY' }
const response = (route, data, status = 200, code = '0000') => route.fulfill({
  status, contentType: 'application/json', body: JSON.stringify({ code, message: code, data, requestId: 'ux03-check' })
})
function mock(context, options = {}) {
  const state = { signedIn: false, attempts: [], operations: new Map(), writes: [], unknownSent: false,
    cancelWrites: [], fundsState: 'UNPAID', orderStatus: options.orderStatus ?? 'WAITING_PAYMENT' }
  const order = () => ({ orderId: 'order-1', purchaseIntentId: 'intent-1', confirmationId: 'confirmation-1', version: '1',
    status: state.orderStatus, product: { goodsId: 'sku', productVersion: '1', name: '验收商品', imageUrl: null },
    offer, quantity: 1, mode: 'OPEN', requestedTeamId: null, createdAt: new Date().toISOString(),
    reserveWaitDeadline: new Date(Date.now() + 300000).toISOString(), paymentEnabled: state.orderStatus === 'WAITING_PAYMENT',
    paymentSummary: state.attempts.length ? { paymentId: 'pay-1', fundsState: state.fundsState, aAcceptance: 'ACCEPTED' } : null,
    fulfillmentSummary: options.fulfillment ?? null, canCancel: options.canCancel ?? state.orderStatus === 'WAITING_PAYMENT',
    updatedAt: new Date().toISOString(), reviewRequired: false, errorCode: null, teamId: 'team-1',
    aOrderId: null, aRecordVersion: null, aTeamVersion: null, aOrderStatus: null, aTeamStatus: 'FORMING',
    paymentDeadline: new Date(Date.now() + 300000).toISOString(), closedAt: null, closeBasis: null,
    refundSummary: options.refund ?? null })
  const payment = () => ({ orderId: 'order-1', simulated: true, notice: '', canCreateAttempt: state.orderStatus === 'WAITING_PAYMENT' &&
    (!state.attempts.length || state.attempts.at(-1).state === 'FAILED'), payment: state.attempts.length ? {
      paymentId: 'pay-1', orderId: 'order-1', version: '1', simulated: true, fundsState: state.fundsState,
      gate: 'OPEN', aAcceptance: state.fundsState === 'SUCCEEDED' ? 'ACCEPTED' : 'NOT_SENT',
      amount: '90.00', currency: 'CNY', paymentDeadline: new Date(Date.now() + 300000).toISOString(),
      paidAt: state.fundsState === 'SUCCEEDED' ? new Date().toISOString() : null,
      activeAttemptId: state.attempts.at(-1).attemptId, successAttemptId: state.fundsState === 'SUCCEEDED' ? state.attempts.at(-1).attemptId : null,
      attempts: state.attempts, allowedActions: [], reviewRequired: false, errorCode: null } : null })
  context.route('**/api/v1/**', async route => {
    const endpoint = new URL(route.request().url()).pathname.replace('/api/v1', '')
    if (endpoint === '/auth/refresh') return state.signedIn ? response(route, { accessToken: 'token', expiresIn: 3600, user: person }) : response(route, null, 401, 'AUTH_REQUIRED')
    if (endpoint === '/auth/csrf') return response(route, { token: 'csrf', headerName: 'X-CSRF' })
    if (endpoint === '/auth/login') { state.signedIn = true; return response(route, { accessToken: 'token', expiresIn: 3600, user: person }) }
    if (endpoint === '/auth/logout') { state.signedIn = false; return response(route, null) }
    if (endpoint === '/orders/order-1') return response(route, order())
    if (endpoint === '/orders' && route.request().method() === 'GET') return options.listFailure
      ? response(route, null, 503, 'DEPENDENCY_UNAVAILABLE')
      : response(route, { items: [order()], page: 1, size: 20, total: 1 })
    if (endpoint === '/orders/order-1/payment' && route.request().method() === 'GET') return response(route, payment())
    if (endpoint.startsWith('/orders/order-1/payment-operations/')) {
      const key = endpoint.split('/').at(-1)
      return state.operations.has(key) ? response(route, state.operations.get(key)) : response(route, null, 404, 'PAYMENT_OPERATION_NOT_FOUND')
    }
    if (endpoint === '/orders/order-1/payment-attempts' && route.request().method() === 'POST') {
      const body = JSON.parse(route.request().postData())
      state.writes.push({ action: 'CREATE', ...body })
      if (options.delayCreate) await new Promise(resolve => setTimeout(resolve, 200))
      if (options.unknownCreate && !state.unknownSent) {
        state.unknownSent = true
        if (!options.unknownCreateNotFound) state.operations.set(body.operationId, { progress: 'PENDING', receipt: { operationId: body.operationId }, attempt: null })
        return route.abort('failed')
      }
      const attemptId = `attempt-${state.attempts.length + 1}`
      const attempt = { orderId: 'order-1', paymentId: 'pay-1', attemptId, attemptNo: String(state.attempts.length + 1),
        version: '1', state: 'OPEN', amount: '90.00', currency: 'CNY', paymentDeadline: new Date(Date.now() + 300000).toISOString(),
        paidAt: null, channelTransactionId: null, canSelectResult: true, errorCode: null }
      state.attempts.push(attempt)
      state.operations.set(body.operationId, { progress: 'APPLIED', receipt: { operationId: body.operationId }, attempt })
      return response(route, { operationId: body.operationId, accepted: true, attemptId }, 202)
    }
    if (endpoint === '/payments/pay-1/attempts/' + state.attempts.at(-1)?.attemptId + '/simulated-results') {
      const body = JSON.parse(route.request().postData())
      state.writes.push({ action: 'RESULT', ...body })
      if (options.unknownResult && !state.unknownSent) {
        state.unknownSent = true
        state.operations.set(body.operationId, { progress: 'PENDING', receipt: { operationId: body.operationId }, attempt: state.attempts.at(-1) })
        return route.abort('failed')
      }
      state.attempts.at(-1).state = body.result
      state.attempts.at(-1).canSelectResult = false
      if (body.result === 'SUCCEEDED') { state.fundsState = 'SUCCEEDED'; state.orderStatus = 'PAID_WAITING_TEAM' }
      state.operations.set(body.operationId, { progress: 'APPLIED', receipt: { operationId: body.operationId }, attempt: state.attempts.at(-1) })
      return response(route, { operationId: body.operationId, accepted: true }, 202)
    }
    if (endpoint === '/orders/order-1/cancel' && route.request().method() === 'POST') {
      const body = JSON.parse(route.request().postData())
      state.cancelWrites.push(body)
      if (options.unknownCancel && state.cancelWrites.length === 1) return route.abort('failed')
      state.orderStatus = 'CLOSING'
      return response(route, order(), 202)
    }
    throw Error(`Unexpected UX-03 API: ${endpoint}`)
  })
  return state
}
async function login(page, target = '/orders/order-1/payment') {
  await page.goto(`${origin}/login?returnTo=${encodeURIComponent(target)}`)
  await page.locator('#loginName').fill('buyer_ux03')
  await page.locator('#password').fill('123456789012')
  await page.locator('form button[type="submit"]').click()
}
const server = await createServer({ server: { host: '127.0.0.1', port: 5184, strictPort: true } })
await server.listen()
const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true, args: ['--no-sandbox', '--no-proxy-server'] })
try {
  {
    const context = await browser.newContext()
    const state = mock(context)
    const page = await context.newPage()
    await login(page)
    await page.getByRole('button', { name: '模拟支付成功', exact: true }).waitFor()
    assert.equal(state.writes.length, 0)
    await page.getByRole('button', { name: '模拟支付成功', exact: true }).click()
    await page.getByText('模拟支付已成功').waitFor()
    assert.deepEqual(state.writes.map(w => w.action), ['CREATE', 'RESULT'])
    await page.reload()
    await page.getByText('模拟支付已成功').waitFor()
    assert.equal(state.writes.length, 2)
    await page.screenshot({ path: path.join(evidence, 'payment-desktop.png'), fullPage: true })
    await context.close()
  }
  {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } })
    const state = mock(context)
    const page = await context.newPage()
    await login(page)
    await page.getByRole('button', { name: '模拟本次支付失败' }).click()
    await page.getByText('本次模拟支付失败').first().waitFor()
    assert.equal(state.writes.length, 2)
    await page.getByRole('button', { name: '再次模拟支付成功' }).click()
    await page.getByText('模拟支付已成功').waitFor()
    assert.equal(state.writes.length, 4)
    assert.equal(state.writes[2].previousAttemptId, 'attempt-1')
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    await page.screenshot({ path: path.join(evidence, 'payment-mobile.png'), fullPage: true })
    await context.close()
  }
  {
    const context = await browser.newContext()
    const state = mock(context, { unknownCreate: true })
    const page = await context.newPage()
    await login(page)
    await page.getByRole('button', { name: '模拟支付成功', exact: true }).click()
    await page.getByText('原操作结果尚未确定').waitFor()
    assert.equal(state.writes.length, 1)
    await page.reload()
    await page.getByText('原操作结果尚未确定').waitFor()
    assert.equal(state.writes.length, 1)
    await page.getByRole('button', { name: '用原编号重试' }).click()
    await page.getByRole('button', { name: '继续本次模拟支付' }).waitFor()
    assert.equal(state.writes.length, 2)
    assert.equal(state.writes[1].operationId, state.writes[0].operationId)
    await page.getByRole('button', { name: '继续本次模拟支付' }).click()
    await page.getByText('模拟支付已成功').waitFor()
    assert.equal(state.writes.length, 3)
    await context.close()
  }
  {
    const context = await browser.newContext()
    const state = mock(context, { unknownResult: true })
    const page = await context.newPage()
    await login(page)
    await page.getByRole('button', { name: '模拟支付成功', exact: true }).click()
    await page.getByText('原操作结果尚未确定').waitFor()
    assert.deepEqual(state.writes.map(w => w.action), ['CREATE', 'RESULT'])
    await page.reload()
    await page.getByText('原操作结果尚未确定').waitFor()
    assert.equal(state.writes.length, 2)
    assert.equal(await page.getByRole('button', { name: '模拟支付成功', exact: true }).count(), 0)
    await page.goto(`${origin}/account`)
    await page.getByRole('button', { name: '退出登录' }).click()
    await page.getByRole('heading', { name: '欢迎回来' }).waitFor()
    await page.goto(`${origin}/login?returnTo=/orders/order-1/payment`)
    await page.locator('#loginName').fill('buyer_ux03')
    await page.locator('#password').fill('123456789012')
    await page.locator('form button[type="submit"]').click()
    await page.getByText('原操作结果尚未确定').waitFor()
    assert.equal(state.writes.length, 2)
    await page.getByRole('button', { name: '用原编号重试' }).click()
    await page.getByText('模拟支付已成功').waitFor()
    assert.equal(state.writes.length, 3)
    assert.equal(state.writes[2].operationId, state.writes[1].operationId)
    await context.close()
  }
  {
    const context = await browser.newContext()
    const state = mock(context, { unknownCreate: true, unknownCreateNotFound: true })
    const page = await context.newPage()
    await login(page)
    await page.getByRole('button', { name: '模拟支付成功', exact: true }).click()
    await page.getByText('原操作结果尚未确定').waitFor()
    await page.reload()
    await page.getByText('原操作结果尚未确定').waitFor()
    assert.equal(state.writes.length, 1)
    await page.getByRole('button', { name: '用原编号重试' }).click()
    await page.getByRole('button', { name: '继续本次模拟支付' }).waitFor()
    assert.equal(state.writes[1].operationId, state.writes[0].operationId)
    await context.close()
  }
  {
    const context = await browser.newContext()
    const state = mock(context)
    const first = await context.newPage()
    await login(first)
    const second = await context.newPage()
    await second.goto(`${origin}/orders/order-1/payment`)
    await Promise.all([first.getByRole('button', { name: '模拟支付成功', exact: true }).waitFor(),
      second.getByRole('button', { name: '模拟支付成功', exact: true }).waitFor()])
    await Promise.all([first.getByRole('button', { name: '模拟支付成功', exact: true }).click(),
      second.getByRole('button', { name: '模拟支付成功', exact: true }).click()])
    await first.getByText('模拟支付已成功').waitFor()
    assert.deepEqual(state.writes.map(w => w.action), ['CREATE', 'RESULT'])
    await context.close()
  }
  {
    const context = await browser.newContext()
    const state = mock(context, { unknownCancel: true })
    const page = await context.newPage()
    await login(page, '/orders/order-1')
    await page.getByRole('button', { name: '取消未付款订单' }).click()
    assert.equal(state.cancelWrites.length, 0)
    await page.getByRole('button', { name: '确认申请关闭' }).click()
    await page.getByText('关闭结果待核对').waitFor()
    await page.reload()
    await page.getByText('关闭结果待核对').waitFor()
    assert.equal(state.cancelWrites.length, 1)
    await page.getByRole('button', { name: '用原编号重试关闭' }).click()
    assert.equal(state.cancelWrites.length, 2)
    assert.equal(state.cancelWrites[0].operationId, state.cancelWrites[1].operationId)
    await context.close()
  }
  {
    const context = await browser.newContext()
    const state = mock(context, { delayCreate: true })
    const first = await context.newPage()
    await login(first)
    const second = await context.newPage()
    await second.goto(`${origin}/orders/order-1/payment`)
    await second.getByRole('button', { name: '模拟支付成功', exact: true }).waitFor()
    await first.getByRole('button', { name: '模拟本次支付失败' }).click()
    for (let i = 0; i < 40 && !state.writes.length; i++) await first.waitForTimeout(25)
    assert.equal(state.writes.length, 1)
    await second.getByRole('button', { name: '模拟支付成功', exact: true }).click()
    await first.getByText('本次模拟支付失败').first().waitFor()
    await second.getByText('付款记录已经变化，请核对后重新选择。').waitFor()
    assert.deepEqual(state.writes.map(w => w.action), ['CREATE', 'RESULT'])
    assert.equal(state.attempts.length, 1)
    await context.close()
  }
  {
    const context = await browser.newContext()
    const state = mock(context, { orderStatus: 'WAITING_REFUND', canCancel: false,
      refund: { refundId: 'refund-1', orderId: 'order-1', paymentId: 'pay-1', refundAmount: '90.00',
        currency: 'CNY', fundsStatus: 'SUCCEEDED', syncStatus: 'PENDING', releaseStatus: 'READY', version: '1', refundedAt: new Date().toISOString() } })
    const page = await context.newPage()
    await login(page, '/orders/order-1')
    await page.getByText('退款已成功，订单正在收尾').first().waitFor()
    assert.equal(await page.getByRole('button', { name: '取消未付款订单' }).count(), 0)
    assert.equal(state.cancelWrites.length, 0)
    await context.close()
  }
  {
    const context = await browser.newContext()
    const state = mock(context, { orderStatus: 'PAID_WAITING_TEAM', canCancel: false })
    const page = await context.newPage()
    await login(page, '/orders/order-1')
    await page.getByText('拼团中').first().waitFor()
    assert.equal(await page.getByRole('button', { name: '取消未付款订单' }).count(), 0)
    assert.equal(state.cancelWrites.length, 0)
    await context.close()
  }
  {
    const context = await browser.newContext()
    mock(context, { listFailure: true })
    const page = await context.newPage()
    await login(page, '/orders')
    await page.getByRole('alert').waitFor()
    assert.equal(await page.getByText('暂无订单，可从商城首页选择商品。').count(), 0)
    await context.close()
  }
  {
    const context = await browser.newContext()
    mock(context, { orderStatus: 'GROUP_COMPLETED', canCancel: false,
      fulfillment: { status: 'PENDING', confirmedAt: new Date().toISOString(), paymentId: 'pay-1', teamId: 'team-1' } })
    const page = await context.newPage()
    await login(page, '/orders/order-1')
    await page.getByText('成团成功，待履约').first().waitFor()
    assert.equal(await page.getByRole('button', { name: '取消未付款订单' }).count(), 0)
    await context.close()
  }
  {
    const context = await browser.newContext()
    mock(context, { orderStatus: 'CLOSED', canCancel: false,
      refund: { refundId: 'refund-2', orderId: 'order-1', paymentId: 'pay-1', refundAmount: '90.00',
        currency: 'CNY', fundsStatus: 'SUCCEEDED', syncStatus: 'ACCEPTED', releaseStatus: 'RELEASED', version: '1', refundedAt: new Date().toISOString() } })
    const page = await context.newPage()
    await login(page, '/orders/order-1')
    await page.getByText('已全额退款，订单已关闭').waitFor()
    await context.close()
  }
  {
    const context = await browser.newContext()
    const state = mock(context, { unknownResult: true })
    const page = await context.newPage()
    await login(page)
    await page.getByRole('button', { name: '模拟支付成功', exact: true }).click()
    await page.getByText('原操作结果尚未确定').waitFor()
    const result = state.writes.at(-1)
    state.operations.set(result.operationId, { progress: 'APPLIED', receipt: { operationId: result.operationId }, attempt: state.attempts.at(-1) })
    state.attempts.at(-1).state = 'SUCCEEDED'; state.attempts.at(-1).canSelectResult = false
    state.fundsState = 'SUCCEEDED'; state.orderStatus = 'PAID_WAITING_TEAM'
    await page.getByRole('button', { name: '刷新付款状态' }).click()
    await page.getByText('模拟支付已成功').waitFor()
    assert.equal(state.writes.length, 2)
    await context.close()
  }
  console.log('UX03_FLOW_PASS success/failure-retry/unknown-create/unknown-404/unknown-result/relogin/late-result/two-tabs/cancel/paid/completed/refund/mobile')
} finally { await browser.close(); await server.close() }
