/** One fresh, two-buyer simulated group purchase on the adopted stable main stack. */
import fs from 'node:fs'
import path from 'node:path'
import https from 'node:https'
import {randomUUID} from 'node:crypto'

const [rootArg, reportArg] = process.argv.slice(2)
if (!rootArg || !reportArg) throw Error('Stable root and report path required')
const root = path.resolve(rootArg)
const report = path.resolve(reportArg)
if (root.toLowerCase() !== path.resolve('D:/Java/zj-market-stable').toLowerCase()) throw Error('Wrong stable root')
if (!report.startsWith(path.resolve('D:/Java/zj-market/target/stable-isolation') + path.sep)) throw Error('Unsafe report path')
const privateManifest = JSON.parse(fs.readFileSync(path.join(root, 'private/files-manifest.json')))
const privateFile = name => path.join(root, 'private', privateManifest.probe[name].relativePath)
const ca = fs.readFileSync(privateFile('web-ca.pem'))
const accounts = JSON.parse(fs.readFileSync(privateFile('demo-accounts.json')))
const goods = fs.readFileSync(privateFile('seed-goods-id.txt'), 'utf8').trim()
const origin = 'https://zj-market.test'
const wait = ms => new Promise(resolve => setTimeout(resolve, ms))
async function until(work, accept, label, seconds = 120) {
  const deadline = Date.now() + seconds * 1000
  do { const value = await work(); if (accept(value)) return value; await wait(1500) }
  while (Date.now() < deadline)
  throw Error('Timed out: ' + label)
}
class Client {
  token = ''
  cookies = new Map()
  async raw(route, method = 'GET', body, extra = {}) {
    return new Promise((resolve, reject) => {
      const req = https.request({hostname: 'zj-market.test', port: 443, path: '/api/v1' + route,
        method, ca, rejectUnauthorized: true, family: 4, autoSelectFamily: false,
        lookup: (_host, _options, callback) => callback(null, '127.0.0.1', 4),
        headers: {Origin: origin, 'Content-Type': 'application/json',
          Cookie: [...this.cookies].map(([key, value]) => key + '=' + value).join('; '),
          ...(this.token ? {Authorization: 'Bearer ' + this.token} : {}), ...extra}}, res => {
        if (!res.socket.authorized) { reject(Error('TLS not authorized')); return }
        for (const cookie of res.headers['set-cookie'] ?? []) {
          const first = cookie.split(';')[0]; const i = first.indexOf('=')
          this.cookies.set(first.slice(0, i), first.slice(i + 1))
        }
        let raw = ''
        res.on('data', chunk => raw += chunk)
        res.on('end', () => {
          try { resolve({status: res.statusCode, body: JSON.parse(raw)}) }
          catch { reject(Error('Non-JSON API response')) }
        })
      })
      req.on('error', reject)
      req.setTimeout(15000, () => req.destroy(Error('HTTPS timeout')))
      if (body !== undefined) req.write(JSON.stringify(body))
      req.end()
    })
  }
  async api(route, method = 'GET', body, statuses = [200]) {
    const response = await this.raw(route, method, body)
    if (!statuses.includes(response.status) || response.body.code !== '0000')
      throw Error('API ' + route + ' ' + response.status + '/' + response.body.code)
    return response.body.data
  }
  async login(credentials) {
    const csrf = await this.api('/auth/csrf')
    const response = await this.raw('/auth/login', 'POST', credentials, {[csrf.headerName]: csrf.token})
    if (response.status !== 200 || response.body.code !== '0000') throw Error('Login failed')
    this.token = response.body.data.accessToken
  }
}

async function purchase(client, mode, teamId) {
  const trial = await client.api('/products/' + goods + '/trial', 'POST', {})
  if (trial.state !== 'AVAILABLE' || trial.offer?.targetCount !== 2 || trial.offer?.payPrice !== '90.00')
    throw Error('Unexpected current offer')
  const confirmation = await client.api('/purchase-confirmations', 'POST',
    {goodsId: goods, mode, ...(teamId ? {teamId} : {}), expectedOffer: trial.offer}, [201])
  const order = await client.api('/orders', 'POST',
    {purchaseIntentId: randomUUID(), confirmationId: confirmation.confirmationId}, [202])
  return until(() => client.api('/orders/' + order.orderId), value => value.status === 'WAITING_PAYMENT',
    'reservation', 90)
}
async function pay(client, orderId) {
  const operationId = randomUUID()
  const attempt = await until(async () => {
    const response = await client.raw('/orders/' + orderId + '/payment-attempts', 'POST',
      {operationId, previousAttemptId: null})
    if (response.body.code === 'PAYMENT_TIME_UNVERIFIABLE') return null
    if (response.body.code !== '0000') throw Error('Payment attempt ' + response.body.code)
    return response.body.data
  }, Boolean, 'payment window', 90)
  if (!attempt.accepted) throw Error('Payment attempt not accepted')
  const current = await until(() => client.api('/orders/' + orderId + '/payment'),
    value => value.payment?.attempts?.some(item => item.canSelectResult), 'attempt selectable')
  const selected = current.payment.attempts.find(item => item.canSelectResult)
  const result = await client.api('/payments/' + current.payment.paymentId + '/attempts/' + selected.attemptId + '/simulated-results',
    'POST', {operationId: randomUUID(), result: 'SUCCEEDED'}, [200, 201, 202])
  if (!result.accepted) throw Error('Simulated result not accepted')
  return until(() => client.api('/orders/' + orderId + '/payment'),
    value => value.payment?.fundsState === 'SUCCEEDED' && value.payment.aAcceptance === 'ACCEPTED',
    'A payment acceptance', 120)
}

const result = {stage: 'ST-03', status: 'RUNNING', goodsId: goods, orders: []}
try {
  const first = new Client(); const second = new Client()
  await first.login(accounts.b06buyer)
  await second.login(accounts.b06buyer2)
  for (const client of [first, second]) {
    const active = await client.api('/products/' + goods + '/active-order')
    if (active) throw Error('Buyer already has active order')
  }
  const opened = await purchase(first, 'OPEN')
  result.orders.push({orderId: opened.orderId, teamId: opened.teamId, mode: 'OPEN'})
  await pay(first, opened.orderId)
  const discovery = await second.api('/products/' + goods + '/joinable-teams?limit=10')
  if (!JSON.stringify(discovery).includes(opened.teamId)) throw Error('Paid team not discoverable')
  const joined = await purchase(second, 'JOIN', opened.teamId)
  if (joined.teamId !== opened.teamId) throw Error('Joined a different team')
  result.orders.push({orderId: joined.orderId, teamId: joined.teamId, mode: 'JOIN'})
  await pay(second, joined.orderId)
  for (const [client, order] of [[first, opened], [second, joined]]) {
    const final = await until(() => client.api('/orders/' + order.orderId),
      value => value.status === 'GROUP_COMPLETED', 'group completion', 180)
    if (final.fulfillmentSummary?.status !== 'PENDING') throw Error('Fulfillment status changed')
  }
  result.status = 'PASSED'
  console.log('ST03_TRANSACTION_PASS ' + result.orders.length)
} catch (error) {
  result.status = 'FAILED'
  result.error = error.message
  throw error
} finally {
  fs.mkdirSync(path.dirname(report), {recursive: true})
  fs.writeFileSync(report, JSON.stringify(result, null, 2) + '\n')
}
