/** Check production discovery exclusions after the TD-06.3 transaction batch. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import https from 'node:https'
import path from 'node:path'
import { createHash } from 'node:crypto'

const root = path.resolve(import.meta.dirname, '../..')
const work = path.join(root, 'target/team-discovery/td06_3_main_20261016_01/browser')
const old = 'D:/Java/zj-market-b-06/.local/b06'
const accounts = JSON.parse(fs.readFileSync(path.join(old, 'control/demo-accounts.json')))
const ca = fs.readFileSync(path.join(old, 'runtime/web-ca.pem'))
const fixture = JSON.parse(fs.readFileSync(path.join(work, 'fixture.json')))
const browser = JSON.parse(fs.readFileSync(path.join(work, 'browser-report.json')))
const cookies = new Map()
let token = ''

function request(route, method = 'GET', body, extra = {}) {
  return new Promise((resolve, reject) => {
    const req = https.request({ hostname: 'zj-market.test', port: 443, path: '/api/v1' + route,
      method, ca, rejectUnauthorized: true, family: 4, autoSelectFamily: false,
      lookup: (_host, _options, cb) => cb(null, '127.0.0.1', 4),
      headers: { Origin: 'https://zj-market.test', 'Content-Type': 'application/json',
        Cookie: [...cookies].map(([key, value]) => key + '=' + value).join('; '),
        ...(token ? { Authorization: 'Bearer ' + token } : {}), ...extra } }, res => {
      for (const value of res.headers['set-cookie'] ?? []) {
        const pair = value.split(';')[0], split = pair.indexOf('=')
        cookies.set(pair.slice(0, split), pair.slice(split + 1))
      }
      let raw = ''
      res.on('data', part => { raw += part })
      res.on('end', () => { try { resolve({ status: res.statusCode, body: JSON.parse(raw) }) } catch (error) { reject(error) } })
    })
    req.on('error', reject)
    req.setTimeout(15000, () => req.destroy(Error('HTTPS timeout')))
    if (body !== undefined) req.write(JSON.stringify(body))
    req.end()
  })
}

const checks = []
const check = (condition, name) => { assert(condition, name); checks.push(name); console.log('PASS ' + name) }
const csrf = await request('/auth/csrf')
check(csrf.status === 200 && csrf.body.code === '0000', 'csrf-ready')
const login = await request('/auth/login', 'POST', accounts.b06buyer2,
  { [csrf.body.data.headerName]: csrf.body.data.token })
check(login.status === 200 && login.body.code === '0000', 'buyer-login')
token = login.body.data.accessToken
const allowed = ['teamId', 'targetCount', 'reservedCount', 'paidCount', 'availableSlots', 'remainingPaidCount', 'validEndTime']
for (const kind of ['success', 'expiry', 'cancel']) {
  const goods = fixture.goods[kind]
  const expectedTeam = Object.values(browser.orders).find(order => order.goods === goods)?.teamId
  check(!!expectedTeam, kind + '-batch-team-recorded')
  const response = await request('/products/' + goods + '/joinable-teams?limit=3')
  check(response.status === 200 && response.body.code === '0000', kind + '-discovery-readable')
  const data = response.body.data
  check(!data.items.some(item => item.teamId === expectedTeam), kind + '-terminal-or-unpaid-team-not-recommended')
  check(data.items.every(item => Object.keys(item).every(key => allowed.includes(key))), kind + '-public-items-no-order-payment-owner-data')
}
const report = { stage: 'TD-06.3', status: 'PASSED', target: 'main443',
  checks, scriptSha256: createHash('sha256').update(fs.readFileSync(import.meta.filename)).digest('hex') }
fs.writeFileSync(path.join(work, 'discovery-readonly.json'), JSON.stringify(report, null, 2) + '\n')
