import { ref, watch } from 'vue'
import { request, write, user } from './auth'
import type { InventoryRequest, InventoryResult, PendingInventory } from '../types/inventory'
const prefix = 'b-inventory-pending:'
export const pendingInventory = ref<PendingInventory[]>([])
export const lastInventoryResult = ref<InventoryResult | null>(null)
const inFlight = new Set<string>()
const key = (uid: string, goods: string) => prefix + uid + ':' + goods
function owner() {
  const u = user.value
  if (!u?.roles.includes('OPERATOR')) throw new Error('请使用运营账号登录。')
  return u.userId
}
function read(uid: string, goods: string): PendingInventory | null {
  const raw = localStorage.getItem(key(uid, goods))
  if (!raw) return null
  const p = JSON.parse(raw) as PendingInventory
  if (p.userId !== uid || p.request?.goodsId !== goods || !p.operationId || !p.request.reason ||
      !['INBOUND','ADJUST'].includes(p.request.kind) || !Number.isFinite(p.createdAt)) throw new Error('恢复记录无法识别，请联系维护人员核对，勿重复入库。')
  return p
}
export function loadPendingInventory() {
  const uid = user.value?.roles.includes('OPERATOR') ? user.value.userId : null
  pendingInventory.value = []
  if (!uid) return
  const result: PendingInventory[] = []
  for (let n=0;n<localStorage.length;n++) {
    const k = localStorage.key(n)
    if (k?.startsWith(prefix + uid + ':')) {
      const p = read(uid, k.slice((prefix + uid + ':').length))
      if (p) result.push(p)
    }
  }
  pendingInventory.value = result
}
const timeout = <T>(p: Promise<T>): Promise<T> => new Promise((resolve,reject) => {
  const timer=setTimeout(() => reject(new Error('结果尚未确认，请查询原操作，勿重复提交。')),10000)
  p.then(resolve,reject).finally(() => clearTimeout(timer))
})
function matches(a: InventoryRequest,b: InventoryRequest) {
  return a.kind===b.kind && a.goodsId===b.goodsId && a.delta===b.delta && a.expectedVersion===b.expectedVersion && a.reason===b.reason
}
function accept(p: PendingInventory,r: InventoryResult) {
  if (user.value?.userId !== p.userId) return
  if (r.operationId !== p.operationId || !matches(p.request,r.request) || !['SUCCEEDED','REJECTED'].includes(r.outcome))
    throw new Error('操作结果与恢复信息不一致，请联系维护人员核对。')
  const latest=read(p.userId,p.request.goodsId)
  if (latest?.operationId===p.operationId) localStorage.removeItem(key(p.userId,p.request.goodsId))
  lastInventoryResult.value=r;loadPendingInventory()
}
export async function queryInventoryOperation(p: PendingInventory) {
  if (owner() !== p.userId) throw new Error('登录身份已变化。')
  if (inFlight.has(p.operationId)) return
  inFlight.add(p.operationId)
  try {
    const r=await timeout(request<InventoryResult>('/admin/inventory/operations/'+encodeURIComponent(p.operationId),p.userId))
    accept(p,r)
  } finally { inFlight.delete(p.operationId) }
}
async function send(p: PendingInventory) {
  const q=p.request
  const body={operationId:p.operationId,expectedVersion:q.expectedVersion,reason:q.reason,
    ...(q.kind==='INBOUND'?{quantity:q.delta}:{delta:q.delta})}
  try {
    const r=await timeout(write<InventoryResult>('/admin/inventory/'+encodeURIComponent(q.goodsId)+(q.kind==='INBOUND'?'/inbounds':'/adjustments'),'POST',body,p.userId))
    accept(p,r)
  } catch (error) {
    try { await queryInventoryOperation(p) } catch { /* 404/network failure remains pending. */ }
    if (read(p.userId,q.goodsId)?.operationId===p.operationId) throw error
  }
}
export async function submitInventory(q: InventoryRequest) {
  const uid=owner()
  if (!navigator.locks) throw new Error('请使用支持多标签页协调的现代浏览器。')
  if (!/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(q.goodsId) || !/^[1-9][0-9]{0,18}$/.test(q.expectedVersion) ||
      !/^-?[1-9][0-9]{0,18}$/.test(q.delta) || BigInt(q.delta)<-9223372036854775808n || BigInt(q.delta)>9223372036854775807n ||
      BigInt(q.expectedVersion)>9223372036854775807n || q.kind==='INBOUND' && BigInt(q.delta)<1n ||
      !q.reason.trim() || q.reason.length>256 || /[\u0000-\u001f\u007f-\u009f]|<\s*\/?\s*[A-Za-z][^>]*>/.test(q.reason))
    throw new Error('请检查数量、版本和原因：只接受范围内的整数，原因须为1～256字符纯文本。')
  await navigator.locks.request(key(uid,q.goodsId),async () => {
    if (owner()!==uid) throw new Error('登录身份已变化。')
    if (read(uid,q.goodsId)) throw new Error('该商品仍有待核对操作，请先确认原结果。')
    const p: PendingInventory={userId:uid,operationId:crypto.randomUUID(),request:{...q},createdAt:Date.now()}
    const raw=JSON.stringify(p)
    localStorage.setItem(key(uid,q.goodsId),raw)
    if (localStorage.getItem(key(uid,q.goodsId))!==raw) throw new Error('无法保存恢复信息，尚未提交操作。')
    loadPendingInventory()
    await send(p)
  })
}
export async function retryInventory(p: PendingInventory) {
  const uid=owner()
  if (uid!==p.userId || !navigator.locks) throw new Error('请重新登录并核对原操作。')
  await navigator.locks.request(key(uid,p.request.goodsId),async () => {
    const stored=read(uid,p.request.goodsId)
    if (!stored || stored.operationId!==p.operationId || !matches(stored.request,p.request)) throw new Error('原操作已变化，请刷新核对。')
    await send(stored)
  })
}
watch(() => user.value?.userId,() => {lastInventoryResult.value=null;pendingInventory.value=[];try{loadPendingInventory()}catch{/* The page reports unreadable storage and blocks writes. */}})
