import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright-core';

const root = path.resolve(import.meta.dirname, '../..');
if (path.basename(root) !== 'zj-market-ux') throw new Error('UX worktree required');
const output = path.join(root, '.local/ux00/evidence');
fs.mkdirSync(output, { recursive: true });
const browser = await chromium.launch({
  executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  headless: true,
  args: ['--host-resolver-rules=MAP zj-market.test 127.0.0.1, MAP zj-market-ux.test 127.0.0.1',
    '--no-proxy-server', '--no-sandbox'],
});
try {
  for (const [name, url] of [
    ['stable', 'https://zj-market.test/'],
    ['ux', 'https://zj-market-ux.test:8446/'],
  ]) {
    const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1280, height: 900 } });
    const page = await context.newPage();
    await page.goto(url, { waitUntil: 'domcontentloaded' });
    const title = await page.title();
    if (!title.includes('知集商城')) throw new Error(name + ' browser title mismatch');
    await page.screenshot({ path: path.join(output, name + '-baseline.png'), fullPage: true });
    console.log(name + ' baseline title=' + title);
    await context.close();
  }
  console.log('UX00_BASELINE_SCREENSHOTS_PASS');
} finally { await browser.close(); }
