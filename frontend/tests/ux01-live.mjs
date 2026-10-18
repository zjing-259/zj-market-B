import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { chromium } from 'playwright-core'

const root = path.resolve(import.meta.dirname, '../..')
if (path.basename(root) !== 'zj-market-ux') throw Error('UX worktree required')
const output = path.join(root, '.local/ux01/evidence')
fs.mkdirSync(output, { recursive: true })
const browser = await chromium.launch({
  executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true,
  args: ['--host-resolver-rules=MAP zj-market.test 127.0.0.1, MAP zj-market-ux.test 127.0.0.1', '--no-proxy-server', '--no-sandbox'],
})
try {
  const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1280, height: 900 } })
  const page = await context.newPage()
  await page.goto('https://zj-market.test/', { waitUntil: 'domcontentloaded' })
  assert.match(await page.title(), /知集商城/)
  await page.goto('https://zj-market-ux.test:8446/', { waitUntil: 'domcontentloaded' })
  await page.getByRole('link', { name: '正经商城' }).waitFor()
  assert.equal(await page.title(), '商城首页｜正经商城')
  await page.screenshot({ path: path.join(output, 'live-desktop.png'), fullPage: true })
  await page.goto('https://zj-market-ux.test:8446/login')
  assert.equal(await page.title(), '登录｜正经商城')
  await page.goto('https://zj-market-ux.test:8446/unknown-route')
  await page.getByRole('heading', { name: '没有找到这个页面' }).waitFor()
  await page.goto('https://zj-market-ux.test:8446/')
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: path.join(output, 'live-mobile.png'), fullPage: true })
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
  await context.close()
  console.log('UX01_LIVE_PASS stable-old/ux-brand/routes/mobile')
} finally { await browser.close() }
