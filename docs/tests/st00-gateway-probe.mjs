/** ST-00: strict-TLS, unauthenticated invalid write that cannot create an order. */
import fs from 'node:fs'
import https from 'node:https'

const ca = fs.readFileSync('D:/Java/zj-market-b-06/.local/b06/runtime/web-ca.pem')
const result = await new Promise((resolve, reject) => {
  const request = https.request({ hostname: 'zj-market.test', port: 443,
    path: '/api/v1/orders', method: 'POST', ca, rejectUnauthorized: true,
    family: 4, autoSelectFamily: false,
    lookup: (_host, _options, callback) => callback(null, '127.0.0.1', 4),
    headers: { Origin: 'https://zj-market.test', 'Content-Type': 'application/json' } }, response => {
    const tlsAuthorized = response.socket.authorized
    let raw = ''
    response.on('data', part => { raw += part })
    response.on('end', () => {
      let body
      try { body = JSON.parse(raw) } catch { reject(Error('Gateway returned non-JSON')); return }
      resolve({ tlsAuthorized, status: response.statusCode,
        contentType: String(response.headers['content-type'] ?? ''),
        code: body.code, apiEnvelope: typeof body.code === 'string' && typeof body.message === 'string' })
    })
  })
  request.on('error', reject)
  request.setTimeout(15000, () => request.destroy(Error('Gateway probe timeout')))
  request.write('{}')
  request.end()
})
if (!result.tlsAuthorized || !result.contentType.includes('application/json') ||
    !result.apiEnvelope || ![400, 401, 403].includes(result.status)) {
  throw Error('Main gateway invalid-write response is not an open JSON API rejection')
}
console.log(JSON.stringify(result))
