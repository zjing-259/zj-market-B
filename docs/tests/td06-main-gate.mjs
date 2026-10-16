import https from 'node:https';
import fs from 'node:fs';
import path from 'node:path';

const mode = process.argv[2];
const root = 'D:/Java/zj-market-b-06';
const ca = fs.readFileSync(path.join(root, '.local/b06/runtime/web-ca.pem'));
const accounts = JSON.parse(fs.readFileSync(path.join(root, '.local/b06/control/demo-accounts.json')));
const goods = fs.readFileSync(path.join(root, '.local/b06/control/seed-goods-id.txt'), 'utf8').trim();
if (!['off', 'on'].includes(mode)) throw Error('off or on required');
let cookie = '';
async function request(route, method = 'GET', body, token, csrf) {
  return new Promise((resolve, reject) => {
    const req = https.request({
      hostname: 'zj-market.test', port: 443, path: '/api/v1' + route, method,
      ca, rejectUnauthorized: true, family: 4, autoSelectFamily: false,
      lookup: (_host, _options, callback) => callback(null, '127.0.0.1', 4),
      headers: { Origin: 'https://zj-market.test', 'Content-Type': 'application/json', Cookie: cookie,
        ...(token ? { Authorization: 'Bearer ' + token } : {}),
        ...(csrf ? { [csrf.headerName]: csrf.token } : {}) }
    }, response => {
      const tlsAuthorized = response.socket.authorized;
      const cookies = response.headers['set-cookie'];
      if (cookies?.length) cookie = cookies.map(value => value.split(';')[0]).join('; ');
      let raw = '';
      response.on('data', chunk => raw += chunk);
      response.on('end', () => {
        let parsed;
        try { parsed = JSON.parse(raw); } catch { parsed = { raw }; }
        resolve({ status: response.statusCode, body: parsed, tlsAuthorized });
      });
    });
    req.on('error', reject);
    req.setTimeout(15000, () => req.destroy(Error('TLS request timeout')));
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}
const csrf = await request('/auth/csrf');
if (csrf.status !== 200 || !csrf.tlsAuthorized) throw Error('TLS/CSRF failed');
const login = await request('/auth/login', 'POST', accounts.b06buyer, undefined, csrf.body.data);
if (login.status !== 200 || login.body.code !== '0000') throw Error('Original buyer login failed');
const result = await request('/products/' + goods + '/joinable-teams', 'GET', undefined, login.body.data.accessToken);
if (mode === 'off' && result.status !== 404) throw Error('Discovery off expected 404, got ' + result.status);
if (mode === 'on' && (result.status !== 200 || result.body.code !== '0000'))
  throw Error('Discovery on expected signed query success, got ' + result.status + '/' + result.body.code);
console.log('TD062_443_GATE_PASS ' + mode + ' ' + result.status);
