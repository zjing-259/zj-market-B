import { chromium } from 'playwright-core';
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '../..');
if (path.basename(root) !== 'zj-market-ux') throw new Error('UX worktree required');
const profile = path.join(root, '.local/st04/browser-profile');
const stableProfile = 'D:/Java/zj-market-stable/state/browser-profile';
if (path.resolve(profile).toLowerCase() === path.resolve(stableProfile).toLowerCase()) {
  throw new Error('Browser profiles overlap');
}
fs.mkdirSync(profile, { recursive: true });
const browser = await chromium.launchPersistentContext(profile, {
  executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  headless: true,
  // TLS identity is checked separately with each site's pinned CA; this run
  // checks profile and cookie isolation without modifying the OS trust store.
  ignoreHTTPSErrors: true,
  args: ['--host-resolver-rules=MAP zj-market-ux.test 127.0.0.1', '--no-proxy-server'],
});
try {
  const page = browser.pages()[0] ?? await browser.newPage();
  await page.goto('https://zj-market-ux.test:8446/', { waitUntil: 'domcontentloaded' });
  if (await page.title() !== '知集商城 · UX 测试站') throw new Error('UX browser title mismatch');
  await browser.addCookies([{ name: 'st04-profile-probe', value: 'ux',
    url: 'https://zj-market-ux.test:8446/' }]);
  const uxCookies = await browser.cookies('https://zj-market-ux.test:8446/');
  const stableCookies = await browser.cookies('https://zj-market.test/');
  if (!uxCookies.some(c => c.name === 'st04-profile-probe') ||
      stableCookies.some(c => c.name === 'st04-profile-probe')) {
    throw new Error('Host-only cookie crossed the stable hostname');
  }
  console.log('ST04_BROWSER_PASS isolated Edge profile, UX page and host-only cookie');
} finally {
  await browser.close();
}
