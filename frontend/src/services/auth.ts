import type { User, Tokens } from '../types/identity'
import type { Envelope } from '../types/http'
import { ApiError } from '../errors/ApiError'
import { readonly, ref } from 'vue'

const current = ref<User | null>(null)
const sessionEvents = typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel('b-identity') : null
// Access tokens exist only in memory; cookie refresh credentials are never visible to JS.
let accessToken: string | null = null
let expiresAt = 0
let refreshFlight: Promise<void> | null = null
export const user = readonly(current)
const clear = () => { accessToken = null; expiresAt = 0; current.value = null }
sessionEvents?.addEventListener('message', event => { if (event.data === 'logout') clear() })
async function body<T>(response: Response): Promise<T> {
  const result: Envelope<T> = await response.json()
  if (!response.ok) {
    const retry = response.headers.get('Retry-After')
    const seconds = retry && /^(?:0|[1-9][0-9]{0,5})$/.test(retry) ? Number(retry) : undefined
    throw new ApiError(result.code, response.status, result.requestId, result.data, seconds)
  }
  return result.data
}
// Serializes cookie mutations across tabs; never replay a consumed refresh token.
async function locked<T>(work: () => Promise<T>): Promise<T> {
  if (!navigator.locks) throw new Error('请使用支持 Web Locks 的现代浏览器进行登录。')
  return navigator.locks.request('b-identity-cookie', work)
}
async function authPost<T>(path: string, data: object, bearer?: string): Promise<T> {
  return locked(async () => {
    const csrf = await body<{ token: string; headerName: string }>(await fetch('/api/v1/auth/csrf', { credentials: 'same-origin', cache: 'no-store' }))
    return body<T>(await fetch(`/api/v1/auth/${path}`, { method: 'POST', credentials: 'same-origin', cache: 'no-store',
      headers: { 'Content-Type': 'application/json', [csrf.headerName]: csrf.token, ...(bearer ? { Authorization: `Bearer ${bearer}` } : {}) }, body: JSON.stringify(data) }))
  })
}
function accept(tokens: Tokens) { accessToken = tokens.accessToken; expiresAt = Date.now() + tokens.expiresIn * 1000; current.value = tokens.user }
export async function login(loginName: string, password: string) { accept(await authPost<Tokens>('login', { loginName, password })) }
export async function register(loginName: string, password: string, displayName: string) { return authPost<User>('register', { loginName, password, displayName }) }
export async function refresh() {
  if (!refreshFlight) refreshFlight = authPost<Tokens>('refresh', {}).then(accept).catch(error => { clear(); throw error }).finally(() => { refreshFlight = null })
  return refreshFlight
}
export async function logout() {
  // On 503 retain the session and show failure; never claim server logout succeeded.
  await authPost<null>('logout', {}, accessToken ?? undefined); clear(); sessionEvents?.postMessage('logout')
}
export async function request<T>(path: string, expectedUserId?: string): Promise<T> {
  if (!accessToken || expiresAt <= Date.now() + 5000) await refresh()
  const send = () => { if (expectedUserId && current.value?.userId !== expectedUserId) throw new Error('登录身份已变化，请重新核对。'); return fetch(`/api/v1${path}`, { credentials: 'same-origin', cache: 'no-store', headers: { Authorization: `Bearer ${accessToken}` } }) }
  let response = await send()
  if (response.status === 401) { await refresh(); response = await send() }
  return body<T>(response)
}
// Resource writes are sent once. A response loss must never create a second business fact.
export async function write<T>(path: string, method: 'POST' | 'PUT', data: object, expectedUserId?: string): Promise<T> {
  if (!accessToken || expiresAt <= Date.now() + 5000) await refresh()
  if (expectedUserId && current.value?.userId !== expectedUserId) throw new Error('登录身份已变化，请重新核对。')
  return body<T>(await fetch(`/api/v1${path}`, { method, credentials: 'same-origin', cache: 'no-store',
    headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' }, body: JSON.stringify(data) }))
}
export async function publicGet<T>(path: string): Promise<T> {
  return body<T>(await fetch(`/api/v1${path}`, { credentials: 'same-origin', cache: 'no-store' }))
}
export async function restore() {
  try { await refresh() } catch (error) { if (!(error instanceof ApiError && error.status === 401)) throw error }
}
export function explain(error: unknown): string {
  if (error instanceof ApiError) {
    const messages: Record<string, string> = { PAYMENT_DISABLED:'模拟支付暂未开放，已有操作仍会继续核对。', PAYMENT_NOT_FOUND:'支付记录不存在或不可访问。', PAYMENT_ATTEMPT_NOT_FOUND:'该渠道尝试不存在或不可访问。', PAYMENT_OPERATION_NOT_FOUND:'暂未查到原操作，请保留原编号继续核对。', PAYMENT_TIME_UNVERIFIABLE:'暂不能可靠确认付款时间窗口，请稍后核对或重试原操作。', PAYMENT_DEPENDENCY_UNAVAILABLE:'付款资格暂时无法核对，请保留原操作编号稍后重试。', PAYMENT_NOT_ALLOWED:'当前订单暂不能支付，请刷新后核对。', PAYMENT_PREDECESSOR_CONFLICT:'上次尝试已变化，请刷新支付记录后核对。', PAYMENT_ATTEMPT_ACTIVE:'已有支付尝试，请核对原尝试结果。', PAYMENT_RESULT_CONFLICT:'已经受理另一种结果，请核对原操作。', INVALID_CREDENTIALS: '账号或密码错误，或账号不可用。', LOGIN_NAME_UNAVAILABLE: '该登录名已被使用。', VALIDATION_FAILED: '请检查填写内容。', RATE_LIMITED: '操作过于频繁，请稍后再试。', CSRF_INVALID: '页面验证已失效，请重新操作。', FORBIDDEN: '当前账号没有运营权限。', TOKEN_INVALID: '登录已失效，请重新登录。', TOKEN_EXPIRED: '登录已过期，请重新登录。', PRODUCT_SYNC_PENDING: '商品资料正在同步或需要核对，请稍后再试。', PRODUCT_VERSION_MISMATCH: '商品资料已更新，请重新读取后试算。', UPSTREAM_TIMEOUT: '优惠服务响应超时，请稍后重新试算。', INTEGRATION_AUTH_FAILED: '优惠服务暂时不可用，请联系维护人员。', AUTH_REQUIRED: '请登录后查看优惠。', PRODUCT_EDIT_CONFLICT: '商品已被其他人修改，请重新读取后再编辑。', PRODUCT_VERSION_EXHAUSTED: '商品版本已达上限，不能继续编辑。', PRODUCT_NOT_FOUND: '商品不存在或已下架。', RETRY_NOT_ALLOWED: '当前商品版本或同步状态不允许恢复，请重新读取后核对。', UPSTREAM_RESPONSE_INVALID: '营销端响应无法确认，请联系维护人员核对。', DEPENDENCY_UNAVAILABLE: '服务暂时不可用，请稍后重试。' }
    return `${messages[error.code] ?? '请求失败。'}（请求编号 ${error.requestId}）`
  }
  return error instanceof Error ? error.message : '网络连接失败，请重试。'
}
