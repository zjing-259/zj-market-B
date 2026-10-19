// UX-only sample preparation. Credentials stay in memory and the ignored control directory.
import fs from 'node:fs'
import path from 'node:path'
import https from 'node:https'
import { randomUUID } from 'node:crypto'
const root = path.resolve(import.meta.dirname, '..')
if (path.basename(root) !== 'zj-market-ux') throw Error('UX worktree required')
const mode = process.argv[2]
if (!['prepare', 'verify'].includes(mode)) throw Error('Use prepare or verify')
const output = path.join(root, '.local/ux04')
fs.mkdirSync(output, { recursive: true })
const file = path.join(output, 'demo-fixture.json')
const accounts = JSON.parse(fs.readFileSync(path.join(root, '.local/b06/control/demo-accounts.json'), 'utf8'))
const ca = fs.readFileSync(path.join(root, '.local/b06/runtime/web-ca.pem'))
const origin = 'https://zj-market-ux.test:8446'
let access = null
const cookies = new Map()
function direct(route, method = 'GET', data, headers = {}) {
  return new Promise((resolve, reject) => {
    const req = https.request({ hostname: 'zj-market-ux.test', port: 8446, path: '/api/v1' + route, method, ca, family: 4, autoSelectFamily: false,
      rejectUnauthorized: true, lookup: (_host, _options, cb) => cb(null, '127.0.0.1', 4),
      headers: { Origin: origin, 'Content-Type': 'application/json', Cookie: [...cookies].map(([k, v]) => k + '=' + v).join('; '),
        ...(access ? { Authorization: 'Bearer ' + access } : {}), ...headers } }, res => {
      for (const value of res.headers['set-cookie'] ?? []) { const pair = value.split(';')[0], i = pair.indexOf('='); cookies.set(pair.slice(0, i), pair.slice(i + 1)) }
      let text = ''; res.on('data', value => { text += value })
      res.on('end', () => { try { resolve({ status: res.statusCode, ...JSON.parse(text) }) } catch { reject(Error('Untrusted API response')) } })
    })
    req.setTimeout(15000, () => req.destroy(Error('API outcome unknown; retain original fixture')))
    req.on('error', () => reject(Error('API outcome unknown; retain original fixture')))
    if (data !== undefined) req.write(JSON.stringify(data))
    req.end()
  })
}
async function api(route, method = 'GET', data, headers) {
  const result = await direct(route, method, data, headers)
  if (result.code !== '0000') throw Error('API rejected ' + route + ': ' + result.status + '/' + result.code)
  return result.data
}
async function login(key) {
  access = null; cookies.clear()
  const csrf = await api('/auth/csrf')
  const account = accounts[key]
  const tokens = await api('/auth/login', 'POST', { loginName: account.loginName, password: account.password }, { [csrf.headerName]: csrf.token })
  access = tokens.accessToken
}
const save = value => fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n')
let fixture = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : { project: 'zj-market-ux', origin,
  createdAt: new Date().toISOString(), items: [
    { key: 'cup', name: '轻行随身杯', description: '清爽蓝色随身杯示意商品。适合演示两人拼团；使用项目原创插画，不提供真实发货。', price: '99.00', image: 'ux04-cup.svg' },
    { key: 'bag', name: '日常帆布袋', description: '日常收纳帆布袋示意商品。适合演示两人拼团；使用项目原创插画，不提供真实发货。', price: '59.00', image: 'ux04-bag.svg' }
  ] }
if (fixture.project !== 'zj-market-ux' || fixture.origin !== origin || fixture.items.length !== 2) throw Error('Unexpected fixture ownership')
await login('b06operator')
if (mode === 'prepare') {
  save(fixture)
  for (const item of fixture.items) {
    if (!item.goodsId) {
      if (item.createStarted) throw Error('Product create outcome unknown; inspect original list before manual reconciliation')
      item.createStarted = true; save(fixture)
      const product = await api('/admin/products', 'POST', { goodsName: item.name, description: item.description,
        imageUrl: origin + '/demo/' + item.image, originalPrice: item.price, currency: 'CNY', saleStatus: 'ON_SALE' })
      item.goodsId = product.goodsId; save(fixture)
    }
    if (!/^[A-Za-z0-9_-]{1,64}$/.test(item.goodsId)) throw Error('Invalid product ID')
    if (!item.stockRequest) {
      const stock = await api('/admin/inventory/' + item.goodsId)
      item.stockRequest = { operationId: randomUUID(), expectedVersion: stock.version, quantity: '20', reason: 'UX-04 演示商品初始备货' }
      save(fixture)
    }
    const previous = await direct('/admin/inventory/operations/' + item.stockRequest.operationId)
    const result = previous.status === 404
      ? await api('/admin/inventory/' + item.goodsId + '/inbounds', 'POST', item.stockRequest)
      : previous.code === '0000' ? previous.data : null
    if (!result || result.operationId !== item.stockRequest.operationId || result.outcome !== 'SUCCEEDED' || result.inventory.goodsId !== item.goodsId)
      throw Error('Original stock operation not confirmed')
    item.stockConfirmed = true; save(fixture)
  }
  console.log('UX04_DEMO_PREPARED two-products/original-stock-keys')
} else {
  for (const item of fixture.items) {
    const stock = await api('/admin/inventory/' + item.goodsId)
    if (stock.available !== '20' || stock.reserved !== '0' || stock.sold !== '0') throw Error('Initial stock differs; do not reset facts')
  }
  await login('b06buyer')
  if ((await direct('/admin/inventory?page=1&size=20')).status !== 403) throw Error('Buyer operator permission boundary failed')
  for (const item of fixture.items) {
    let product
    for (let n = 0; n < 30; n++) {
      product = await api('/products/' + item.goodsId)
      if (product.syncReady) break
      await new Promise(resolve => setTimeout(resolve, 1000))
    }
    const trial = await api('/products/' + item.goodsId + '/trial', 'POST', {})
    const teams = await api('/products/' + item.goodsId + '/joinable-teams?limit=3')
    if (!product.syncReady || product.goodsName !== item.name || trial.state !== 'AVAILABLE' || trial.offer?.targetCount !== 2 ||
      trial.offer?.activityId !== String(item.activityId) || trial.offer?.payPrice !== (Number(item.price) - 10).toFixed(2) || teams.state !== 'AVAILABLE') throw Error('Demo offer or discovery not ready')
  }
  fixture.verifiedAt = new Date().toISOString(); save(fixture)
  console.log('UX04_DEMO_VERIFIED strict-TLS/two-offers/stock/buyer-403')
}
