export type Page = 'products' | 'admin' | 'inventory' | 'exceptions' | 'refunds' | 'reconciliations' | 'team' | 'orders' | 'payment' | 'account' | 'login' | 'register' | 'not-found'

export function resolvePage(path: string): Page {
  if (path === '/' || path === '/products' || /^\/products\/[^/]+$/.test(path)) return 'products'
  if (path === '/admin/products' || /^\/admin\/products\/[^/]+$/.test(path)) return 'admin'
  if (path === '/admin/inventory') return 'inventory'
  if (path === '/admin/orders' || /^\/admin\/orders\/[^/]+$/.test(path)) return 'exceptions'
  if (path === '/admin/refunds' || /^\/admin\/refunds\/[^/]+$/.test(path)) return 'refunds'
  if (path === '/admin/reconciliations' || /^\/admin\/reconciliations\/[^/]+$/.test(path)) return 'reconciliations'
  if (/^\/teams\/[^/]+$/.test(path)) return 'team'
  if (/^\/orders\/[^/]+\/payment$/.test(path)) return 'payment'
  if (path === '/orders' || /^\/orders\/[^/]+$/.test(path)) return 'orders'
  if (path === '/account') return 'account'
  if (path === '/login') return 'login'
  if (path === '/register') return 'register'
  return 'not-found'
}

export function safeReturnTo(search: string): string | null {
  const path = new URLSearchParams(search).get('returnTo')
  if (!path || !path.startsWith('/') || path.startsWith('//') || /[?#\\\u0000-\u001f\u007f]/.test(path)) return null
  if (/^\/(?:products|orders|account)$/.test(path) || path === '/') return path
  const match = path.match(/^\/(products|teams|orders)\/([^/]+)(\/payment)?$/)
  if (!match || (match[3] && match[1] !== 'orders')) return null
  try {
    const id = decodeURIComponent(match[2]!)
    return id.length > 0 && id.length <= 64 && id.trim() === id && !/[\/\\\u0000-\u001f\u007f]/.test(id) ? path : null
  } catch { return null }
}

export function pageTitle(page: Page): string {
  const names: Record<Page, string> = { products: '商城首页', admin: '商品管理', inventory: '库存管理', exceptions: '订单异常', refunds: '退款异常', reconciliations: '团队核对', team: '团队详情', orders: '我的订单', payment: '模拟收银台', account: '账号中心', login: '登录', register: '注册', 'not-found': '页面不存在' }
  return `${names[page]}｜正经商城`
}

export function go(path: string, replace = false): void {
  if (resolvePage(path.split('?')[0]!) === 'not-found') throw new Error('未知站内路径')
  history[replace ? 'replaceState' : 'pushState'](null, '', path)
  window.dispatchEvent(new PopStateEvent('popstate'))
}
