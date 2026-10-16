/** Prepare a renewable, paid and discoverable team only in the isolated 8445 project. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import https from 'node:https'
import path from 'node:path'
import { createHash, randomInt, randomUUID } from 'node:crypto'
import { createRequire } from 'node:module'
import { spawnSync } from 'node:child_process'

const root = path.resolve(import.meta.dirname, '../..')
const name = process.argv[2]
if (!/^td06_demo_\d{8}_\d{2}$/.test(name ?? '')) throw Error('Use fresh td06_demo_YYYYMMDD_NN batch')
const work = path.join(root, 'target/team-discovery', name)
const resume = process.argv[3] === '--resume'
if (process.argv[3] && !resume) throw Error('Only --resume is supported')
if (fs.existsSync(work) !== resume) throw Error(resume ? 'Failed demo batch missing' : 'Demo batch already exists; use a new name')
const candidate = path.join(root, 'target/team-discovery/td05_20261015_01')
const accounts = JSON.parse(fs.readFileSync(path.join(candidate, 'private/control/demo-accounts.json')))
const ca = fs.readFileSync(path.join(candidate, 'private/runtime/web-ca.pem'))
const { chromium } = createRequire(path.join(root, 'frontend/package.json'))('playwright-core')
const origin = 'https://zj-market.test:8445'
const project = 'zj-market-td05-20261015-01'
const freshReport = { stage: 'TD-06.1', batch: name, target: 'candidate8445', status: 'RUNNING',
  startedAt: new Date().toISOString(), checks: [], validMinutes: 60,
  scriptSha256: createHash('sha256').update(fs.readFileSync(import.meta.filename)).digest('hex') }
const report = resume ? JSON.parse(fs.readFileSync(path.join(work, 'demo-report.json'))) : freshReport
if (resume) {
  if (report.status !== 'FAILED' || !report.goodsId || !report.activityId) throw Error('Only a failed prepared demo can resume')
  fs.copyFileSync(path.join(work, 'demo-report.json'), path.join(work, 'demo-report-failed.json'))
  report.status = 'RUNNING'; report.resumedAt = new Date().toISOString(); delete report.error
  report.resumeScriptSha256 = freshReport.scriptSha256
}
const record = (ok, label) => { assert(ok, label); report.checks.push(label); console.log('PASS ' + label) }
const save = () => fs.writeFileSync(path.join(work, 'demo-report.json'), JSON.stringify(report, null, 2) + '\n')
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))
async function until(read, good, label, seconds = 100) {
  const deadline = Date.now() + seconds * 1000
  while (Date.now() < deadline) { const value = await read(); if (good(value)) return value; await sleep(1000) }
  throw Error('Timeout: ' + label)
}
function dockerSql(sql) {
  const result = spawnSync('docker', ['--context', 'desktop-linux', 'exec', '-i', project + '-mysql-1',
    'sh', '-c', 'MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysql -uroot --batch --skip-column-names'],
  { input: sql, encoding: 'utf8', timeout: 90000 })
  if (result.status !== 0) throw Error('Candidate SQL failed')
  return result.stdout.trim()
}
let token = ''
const cookies = new Map()
function direct(route, method = 'GET', body, extra = {}) {
  return new Promise((resolve, reject) => {
    const request = https.request({ hostname: 'zj-market.test', port: 8445, path: '/api/v1' + route,
      method, ca, rejectUnauthorized: true, family: 4, autoSelectFamily: false,
      lookup: (_host, _options, cb) => cb(null, '127.0.0.1', 4),
      headers: { Origin: origin, 'Content-Type': 'application/json',
        Cookie: [...cookies].map(([key, value]) => key + '=' + value).join('; '),
        ...(token ? { Authorization: 'Bearer ' + token } : {}), ...extra } }, response => {
      for (const line of response.headers['set-cookie'] ?? []) {
        const pair = line.split(';')[0]; const split = pair.indexOf('=')
        cookies.set(pair.slice(0, split), pair.slice(split + 1))
      }
      let raw = ''; response.on('data', chunk => { raw += chunk })
      response.on('end', () => { try { resolve({ status: response.statusCode, body: JSON.parse(raw) }) } catch (error) { reject(error) } })
    })
    request.on('error', reject); request.setTimeout(15000, () => request.destroy(Error('HTTPS timeout')))
    if (body !== undefined) request.write(JSON.stringify(body))
    request.end()
  })
}
async function api(route, method = 'GET', body, headers) {
  const response = await direct(route, method, body, headers)
  if (response.status < 200 || response.status >= 300 || response.body.code !== '0000') throw Error('Candidate API failed: ' + route + ' ' + response.status + '/' + response.body.code)
  return response.body.data
}
async function person(browser, key) {
  const context = await browser.newContext({ ignoreHTTPSErrors: false, viewport: { width: 1280, height: 900 } })
  const page = await context.newPage()
  let bearer = ''
  page.on('response', async response => {
    if (/\/auth\/(login|refresh)$/.test(response.url()) && response.status() === 200)
      bearer = (await response.json()).data.accessToken
  })
  await page.goto(origin + '/login')
  await page.getByLabel('登录名').fill(accounts[key].loginName)
  await page.getByLabel('密码', { exact: true }).fill(accounts[key].password)
  await page.locator('form button[type=submit]').click()
  await page.getByRole('button', { name: '退出登录', exact: true }).waitFor()
  return { page, context, read: async route => {
    const result = await page.evaluate(async ({ route, bearer }) => {
      const response = await fetch('/api/v1' + route, { headers: { Authorization: 'Bearer ' + bearer }, cache: 'no-store' })
      return { status: response.status, body: await response.json() }
    }, { route, bearer })
    if (result.status !== 200 || result.body.code !== '0000') throw Error('Buyer read failed: ' + route)
    return result.body.data
  } }
}

if (!resume) fs.mkdirSync(work, { recursive: false })
save()
let browser
try {
  const ready = spawnSync('python', ['-B', path.join(root, 'scripts/td06-environment.py'), 'ready', '--target', 'candidate8445'],
    { cwd: root, encoding: 'utf8', timeout: 30000 })
  record(ready.status === 0, 'candidate-owner-image-schema-rpc-ready')
  let product = { goodsId: report.goodsId }
  if (!resume) {
    const csrf = await api('/auth/csrf')
    const operator = await api('/auth/login', 'POST', accounts.b06operator, { [csrf.headerName]: csrf.token })
    token = operator.accessToken
    product = await api('/admin/products', 'POST', { goodsName: 'TD06 演示 ' + name,
      description: '请在有效期内由第二位用户从商品页发现并参团', imageUrl: null,
      originalPrice: '100.00', currency: 'CNY', saleStatus: 'ON_SALE' })
    record(/^[a-f0-9-]{36}$/.test(product.goodsId), 'distinct-operator-created-product')
    report.goodsId = product.goodsId
    save()
    const stock = await api('/admin/inventory/' + product.goodsId)
    await api('/admin/inventory/' + product.goodsId + '/inbounds', 'POST',
      { operationId: randomUUID(), quantity: '10', expectedVersion: stock.version, reason: 'TD06.1 isolated demo stock' })
    record(true, 'isolated-inventory-inbound')
    const activityId = 80000000 + randomInt(1000000)
    const discountId = String(7000000 + randomInt(1000000))
    const sql = `USE group_buy_market_b06; START TRANSACTION;
INSERT INTO group_buy_discount(discount_id,discount_name,discount_desc,discount_type,market_plan,market_expr)
VALUES ('${discountId}','TD06 demo','Ten yuan reduction',0,'ZJ','10');
INSERT INTO group_buy_activity(activity_id,activity_name,discount_id,group_type,take_limit_count,target,valid_time,status,start_time,end_time)
VALUES (${activityId},'TD06 demo','${discountId}',1,10,2,60,1,UTC_TIMESTAMP()-INTERVAL 1 HOUR,UTC_TIMESTAMP()+INTERVAL 30 DAY);
INSERT INTO sc_sku_activity(source,channel,activity_id,goods_id) VALUES ('b06','web',${activityId},'${product.goodsId}'); COMMIT;`
    dockerSql(sql)
    report.activityId = activityId
    record(dockerSql(`SELECT COUNT(*) FROM group_buy_market_b06.sc_sku_activity WHERE goods_id='${product.goodsId}' AND activity_id=${activityId};`) === '1', 'candidate-only-hour-long-activity')
    save()
  }
  browser = await chromium.launch({ headless: true,
    executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    args: ['--host-resolver-rules=MAP zj-market.test 127.0.0.1', '--no-proxy-server'] })
  const buyer = await person(browser, 'b06buyer')
  let orderId, order
  if (resume) {
    orderId = dockerSql(`SELECT order_id FROM zj_market_b06.b_market_order WHERE goods_id='${product.goodsId}' ORDER BY created_at_ms DESC LIMIT 1;`)
    record(!!orderId, 'resume-original-order-id')
    order = await buyer.read('/orders/' + orderId)
  } else {
    await buyer.page.goto(origin + '/products/' + product.goodsId)
    const quote = buyer.page.getByRole('button', { name: '核对开团报价', exact: true })
    await until(() => quote.isEnabled(), Boolean, 'buyer open quote ready')
    await quote.click()
    await buyer.page.getByRole('button', { name: '确认购买', exact: true }).click()
    const orderLink = buyer.page.locator('section[aria-label="购买确认"]').getByRole('link', { name: '查看原订单', exact: true })
    await orderLink.waitFor()
    orderId = (await orderLink.getAttribute('href')).split('/')[2]
    order = await until(() => buyer.read('/orders/' + orderId), value => value.status === 'WAITING_PAYMENT', 'real A reservation')
  }
  await buyer.page.goto(origin + '/orders/' + orderId + '/payment')
  const beforePayment = await buyer.read('/orders/' + orderId + '/payment')
  if (!beforePayment.payment?.attempts?.length)
    await buyer.page.getByRole('button', { name: '创建模拟支付尝试', exact: true }).click()
  const chooseSuccess = buyer.page.getByRole('button', { name: '选择模拟成功', exact: true })
  await until(async () => {
    if (await chooseSuccess.isEnabled().catch(() => false)) return true
    const retry = buyer.page.getByRole('button', { name: '重试原操作', exact: true })
    if (await retry.isEnabled().catch(() => false)) await retry.click()
    return false
  }, Boolean, 'simulated success choice ready')
  await chooseSuccess.click()
  const paid = await until(() => buyer.read('/orders/' + orderId + '/payment'),
    value => value.payment?.fundsState === 'SUCCEEDED' && value.payment.aAcceptance === 'ACCEPTED',
    'payment accepted by A')
  record(paid.payment.amount === '90.00', 'buyer-paid-and-A-accepted')
  report.teamId = order.teamId
  report.buyerOrderSha256 = createHash('sha256').update(orderId).digest('hex')
  const second = await person(browser, 'b06buyer2')
  await second.page.goto(origin + '/products/' + product.goodsId)
  await second.page.locator('a[href="/teams/' + encodeURIComponent(order.teamId) + '"]').waitFor()
  record(true, 'second-buyer-discovers-same-team-without-share-link')
  const team = await second.read('/teams/' + encodeURIComponent(order.teamId))
  record(team.teamId === order.teamId && team.joinable === true, 'second-buyer-can-enter-original-JOIN')
  report.teamExpiresAt = team.validEndTime
  report.completedAt = new Date().toISOString()
  report.status = 'PASSED_CANDIDATE_DEMO_READY'
  save()
  console.log('DEMO_READY ' + JSON.stringify({ goodsId: report.goodsId, teamId: report.teamId,
    expiresAt: report.teamExpiresAt, origin }))
} catch (error) {
  report.status = 'FAILED'
  report.error = error.message
  save()
  throw error
} finally { if (browser) await browser.close() }
