import https from 'node:https';
import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
// Explicit local CA, strict certificate and DNS identity verification; no OS trust changes.
const request = https.get({
  hostname: 'zj-market.test', port: 443, path: '/healthz',
  ca: readFileSync(process.argv[2]), rejectUnauthorized: true,
  lookup: (_host, options, callback) => options.all
    ? callback(null, [{ address: '127.0.0.1', family: 4 }])
    : callback(null, '127.0.0.1', 4),
  timeout: 5000,
}, response => {
  assert.equal(response.socket.authorized, true);
  let body = '';
  response.setEncoding('utf8'); response.on('data', chunk => { body += chunk; });
  response.on('end', () => {
    assert.equal(response.statusCode, 200); assert.equal(body, 'UP');
    console.log('HOST_HTTPS_PASS strict CA and hostname verification');
  });
});
request.on('timeout', () => request.destroy(new Error('HTTPS host timeout')));
request.on('error', error => { console.error(error.message); process.exitCode = 1; });
