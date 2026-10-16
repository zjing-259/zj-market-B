/** Strict TLS readback of pre-existing TD-06 orders and access boundaries. */
import fs from 'node:fs'
import path from 'node:path'
import https from 'node:https'

const [rootArg, historicalArg, reportArg] = process.argv.slice(2)
if (!rootArg || !historicalArg || !reportArg) throw Error('Stable root, historical and report paths required')
const root = path.resolve(rootArg)
if (root.toLowerCase() !== path.resolve('D:/Java/zj-market-stable').toLowerCase()) throw Error('Wrong stable root')
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'private/files-manifest.json')))
const privatePath = name => path.join(root, 'private', manifest.probe[name].relativePath)
const ca = fs.readFileSync(privatePath('web-ca.pem'))
const accounts = JSON.parse(fs.readFileSync(privatePath('demo-accounts.json')))
const goods = fs.readFileSync(privatePath('seed-goods-id.txt'), 'utf8').trim()
const historical = JSON.parse(fs.readFileSync(historicalArg)).orders
const completedId = Object.keys(historical).find(id => historical[id].final?.status === 'GROUP_COMPLETED')
const refundId = Object.keys(historical).find(id => historical[id].final?.refundSummary)
if (!completedId || !refundId) throw Error('Historical order fixtures missing')
class Client {
  token = ''
  cookie = ''
  raw(route, method = 'GET', body, extra = {}) {
    return new Promise((resolve, reject) => {
      const req = https.request({hostname: 'zj-market.test', port: 443, path: '/api/v1' + route,
        method, ca, rejectUnauthorized: true, family: 4, autoSelectFamily: false,
        lookup: (_host, _options, callback) => callback(null, '127.0.0.1', 4),
        headers: {Origin: 'https://zj-market.test', 'Content-Type': 'application/json',
          Cookie: this.cookie, ...(this.token ? {Authorization: 'Bearer ' + this.token} : {}), ...extra}}, res => {
        if (!res.socket.authorized) { reject(Error('TLS authorization failed')); return }
        if (res.headers['set-cookie']?.length) this.cookie = res.headers['set-cookie'].map(value => value.split(';')[0]).join('; ')
        let raw = ''
        res.on('data', chunk => raw += chunk)
        res.on('end', () => {
          try { resolve({status: res.statusCode, contentType: res.headers['content-type'], body: JSON.parse(raw)}) }
          catch { reject(Error('Non-JSON API response')) }
        })
      })
      req.on('error', reject)
      req.setTimeout(15000, () => req.destroy(Error('HTTPS timeout')))
      if (body !== undefined) req.write(JSON.stringify(body))
      req.end()
    })
  }
  async login(credentials) {
    const csrf = await this.raw('/auth/csrf')
    if (csrf.status !== 200) throw Error('CSRF failed')
    const login = await this.raw('/auth/login', 'POST', credentials,
      {[csrf.body.data.headerName]: csrf.body.data.token})
    if (login.status !== 200 || login.body.code !== '0000') throw Error('Login failed')
    this.token = login.body.data.accessToken
  }
}
const checks = []
const requireResult = (value, label) => { if (!value) throw Error(label); checks.push(label) }
const anonymous = new Client()
const hidden = await anonymous.raw('/products/' + goods + '/joinable-teams?limit=3')
requireResult(hidden.status === 401 && hidden.contentType?.includes('application/json'), 'anonymous-discovery-denied-json')
const invalid = await anonymous.raw('/orders', 'POST', {})
requireResult(invalid.status === 401 && invalid.body.code === 'AUTH_REQUIRED', 'invalid-write-json')
const buyer = new Client(); const other = new Client()
await buyer.login(accounts.b06buyer); await other.login(accounts.b06buyer2)
const completed = await buyer.raw('/orders/' + completedId)
requireResult(completed.status === 200 && completed.body.data.status === 'GROUP_COMPLETED', 'historical-completed-order-readable')
const refundOrder = await buyer.raw('/orders/' + refundId)
requireResult(refundOrder.status === 200 && refundOrder.body.data.refundSummary?.fundsStatus === 'SUCCEEDED', 'historical-refunded-order-readable')
const refund = await buyer.raw('/orders/' + refundId + '/refund')
requireResult(refund.status === 200 && refund.body.code === '0000', 'historical-refund-detail-readable')
const foreign = await other.raw('/orders/' + completedId)
requireResult(foreign.status === 404, 'other-buyer-order-hidden')
const admin = await buyer.raw('/admin/refunds')
requireResult(admin.status === 403, 'buyer-operator-boundary')
const output = {stage: 'ST-03', status: 'PASSED', checks}
fs.mkdirSync(path.dirname(reportArg), {recursive: true})
fs.writeFileSync(reportArg, JSON.stringify(output, null, 2) + '\n')
console.log('ST03_READBACK_PASS ' + checks.length)
