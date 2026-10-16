/** Strict-TLS, read-only business and harmless invalid-write readiness probe. */
import fs from 'node:fs'
import https from 'node:https'

const [caPath, accountPath, goodsPath] = process.argv.slice(2)
if (!caPath || !accountPath || !goodsPath) throw Error('Three private input paths required')
const ca = fs.readFileSync(caPath)
const buyer = JSON.parse(fs.readFileSync(accountPath, 'utf8')).b06buyer
const goods = fs.readFileSync(goodsPath, 'utf8').trim()
if (!buyer || !/^[0-9a-f-]{36}$/i.test(goods)) throw Error('Probe inputs invalid')
let cookie = ''
async function request(route, method = 'GET', body, token, csrf) {
  return new Promise((resolve, reject) => {
    const req = https.request({hostname: 'zj-market.test', port: 443,
      path: '/api/v1' + route, method, ca, rejectUnauthorized: true,
      family: 4, autoSelectFamily: false,
      lookup: (_host, _options, cb) => cb(null, '127.0.0.1', 4),
      headers: {Origin: 'https://zj-market.test', 'Content-Type': 'application/json',
        Cookie: cookie, ...(token ? {Authorization: 'Bearer ' + token} : {}),
        ...(csrf ? {[csrf.headerName]: csrf.token} : {})}}, res => {
      const tlsAuthorized = res.socket.authorized
      const values = res.headers['set-cookie']
      if (values?.length) cookie = values.map(value => value.split(';')[0]).join('; ')
      let raw = ''
      res.on('data', chunk => raw += chunk)
      res.on('end', () => {
        let payload
        try { payload = JSON.parse(raw) } catch { reject(Error('Non-JSON API response')); return }
        resolve({status: res.statusCode, payload, tlsAuthorized,
          contentType: String(res.headers['content-type'] ?? '')})
      })
    })
    req.on('error', reject)
    req.setTimeout(15000, () => req.destroy(Error('Probe timeout')))
    if (body !== undefined) req.write(JSON.stringify(body))
    req.end()
  })
}
const csrf = await request('/auth/csrf')
if (!csrf.tlsAuthorized || csrf.status !== 200 || csrf.payload.code !== '0000')
  throw Error('CSRF/TLS probe failed')
const login = await request('/auth/login', 'POST', buyer, undefined, csrf.payload.data)
if (login.status !== 200 || login.payload.code !== '0000') throw Error('Login probe failed')
const token = login.payload.data.accessToken
const product = await request('/products/' + goods, 'GET', undefined, token)
if (product.status !== 200 || product.payload.code !== '0000') throw Error('Product probe failed')
const discovery = await request('/products/' + goods + '/joinable-teams', 'GET', undefined, token)
if (discovery.status !== 200 || discovery.payload.code !== '0000') throw Error('Signed discovery probe failed')
cookie = ''
const invalid = await request('/orders', 'POST', {})
if (!invalid.tlsAuthorized || !invalid.contentType.includes('application/json') ||
    ![400, 401, 403].includes(invalid.status) || invalid.payload.code !== 'AUTH_REQUIRED')
  throw Error('Invalid-write gateway probe failed')
console.log(JSON.stringify({status: 'STABLE_PROBE_PASS', product: product.status,
  discovery: discovery.status, invalidWrite: invalid.status, tlsAuthorized: true}))
