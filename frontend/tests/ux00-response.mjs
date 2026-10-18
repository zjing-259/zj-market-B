import assert from 'node:assert/strict';
import { chromium } from 'playwright-core';
import { createServer } from 'vite';

const origin = 'http://127.0.0.1:5181';
const edge = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const server = await createServer({ server: { host: '127.0.0.1', port: 5181, strictPort: true } });
await server.listen();
const browser = await chromium.launch({ executablePath: edge, headless: true, args: ['--no-sandbox'] });
try {
  const page = await browser.newPage();
  let writes = 0;
  let refreshFails = false;
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname;
    const json = (status, data, code = '0000', headers = {}) => route.fulfill({ status,
      contentType: 'application/json', headers,
      body: JSON.stringify({ code, message: code, data, requestId: 'ux00-request' }) });
    if (path === '/api/v1/auth/csrf') return json(200, { token: 'csrf', headerName: 'X-CSRF' });
    if (path === '/api/v1/auth/login') return json(200, { accessToken: 'token', expiresIn: 3600,
      user: { userId: 'buyer', loginName: 'buyer', displayName: 'Buyer', roles: ['USER'] } });
    if (path === '/api/v1/auth/refresh') return refreshFails
      ? route.fulfill({ status: 503, contentType: 'text/html', body: '<html>maintenance secret</html>' })
      : json(401, null, 'AUTH_REQUIRED');
    if (path === '/api/v1/products') return json(200, { items: [], page: 1, size: 20, total: 0 });
    if (path === '/api/v1/ux00-html-503') return route.fulfill({ status: 503, contentType: 'text/html', body: '<html>private proxy detail</html>' });
    if (path === '/api/v1/ux00-html-502') return route.fulfill({ status: 502, contentType: 'text/html', body: '<html>bad gateway</html>' });
    if (path === '/api/v1/ux00-empty') return route.fulfill({ status: 200, contentType: 'application/json', body: '' });
    if (path === '/api/v1/ux00-bad-json') return route.fulfill({ status: 200, contentType: 'application/json', body: '{bad' });
    if (path === '/api/v1/ux00-bad-envelope') return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    if (path === '/api/v1/ux00-429') return json(429, null, 'RATE_LIMITED', { 'Retry-After': '17' });
    if (path === '/api/v1/ux00-write') { writes++; return route.abort('failed'); }
    throw Error('Unexpected route: ' + path);
  });
  await page.goto(origin + '/');
  const result = await page.evaluate(async () => {
    const api = await import('/src/services/auth.ts');
    const test = async path => {
      try { await api.publicGet(path); return { accepted: true }; }
      catch (error) { return { code: error.code, status: error.status, retry: error.retryAfterSeconds,
        message: api.explain(error) }; }
    };
    const cases = await Promise.all(['/ux00-html-503', '/ux00-html-502', '/ux00-empty',
      '/ux00-bad-json', '/ux00-bad-envelope', '/ux00-429'].map(test));
    await api.login('buyer', 'password');
    let writeMessage = '';
    try { await api.write('/ux00-write', 'POST', { operationId: 'original' }, 'buyer'); }
    catch (error) { writeMessage = api.explain(error); }
    return { cases, writeMessage, userBefore: api.user.value?.userId };
  });
  assert.deepEqual(result.cases.map(x => x.code), ['SITE_MAINTENANCE', 'GATEWAY_UNAVAILABLE',
    'INVALID_API_RESPONSE', 'INVALID_API_RESPONSE', 'INVALID_API_RESPONSE', 'RATE_LIMITED']);
  assert.equal(result.cases[5].retry, 17);
  assert.equal(result.userBefore, 'buyer');
  assert.equal(writes, 1);
  assert.match(result.writeMessage, /原操作/);
  assert(!JSON.stringify(result).includes('<html>') && !JSON.stringify(result).includes('Unexpected token'));
  refreshFails = true;
  const after = await page.evaluate(async () => {
    const api = await import('/src/services/auth.ts');
    try { await api.refresh(); } catch { /* maintenance must not erase the known identity */ }
    return api.user.value?.userId;
  });
  assert.equal(after, 'buyer');
  console.log('UX00_RESPONSE_PASS html503/502/empty/badJSON/badEnvelope/429/one-write/session-retained');
  await page.close();
} finally {
  await browser.close();
  await server.close();
}
