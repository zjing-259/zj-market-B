import https from 'node:https';
import fs from 'node:fs';

const ca = fs.readFileSync(process.argv[2]);
const result = await new Promise((resolve, reject) => {
  const request = https.get({
    hostname: 'zj-market-ux.test', port: 8446, path: '/api/v1/system/status',
    ca, rejectUnauthorized: true, family: 4, autoSelectFamily: false,
    lookup: (_host, _options, callback) => callback(null, '127.0.0.1', 4),
    timeout: 10000,
  }, response => {
    let body = '';
    response.setEncoding('utf8');
    response.on('data', chunk => { body += chunk; if (body.length > 4096) request.destroy(new Error('Gateway status too large')); });
    response.on('end', () => {
      try {
        const parsed = JSON.parse(body);
        if (response.statusCode !== 200 || parsed.code !== '0000' ||
            !['NORMAL', 'MAINTENANCE'].includes(parsed.data?.mode)) {
          throw new Error('Gateway status contract mismatch');
        }
        resolve(parsed.data.mode);
      } catch (error) { reject(error); }
    });
  });
  request.on('timeout', () => request.destroy(new Error('Gateway status timeout')));
  request.on('error', reject);
});
console.log(result);
