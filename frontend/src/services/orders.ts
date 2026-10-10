import { request, write, user, explain } from './auth'
import type { Confirmation, Offer, Order, PendingPurchase } from '../types/order'
import { ApiError } from '../errors/ApiError'
const prefix='b-purchase:'
function key(owner:string,goods:string){return prefix+owner+':'+goods}
export function pending(goods:string):PendingPurchase|null {
 const owner=user.value?.userId;if(!owner)return null
 try{const p=JSON.parse(localStorage.getItem(key(owner,goods))??'null');return p&&p.userId===owner&&p.goodsId===goods&&typeof p.purchaseIntentId==='string'&&typeof p.confirmationId==='string'?p:null}catch{return null}
}
export function confirm(goodsId:string,offer:Offer,owner:string,teamId?:string){return write<Confirmation>('/purchase-confirmations','POST',{goodsId,mode:teamId?'JOIN':'OPEN',...(teamId?{teamId}:{}),expectedOffer:offer},owner)}
export async function submit(goodsId:string,confirmationId:string,owner:string):Promise<Order>{
 if(!navigator.locks)throw new Error('请使用支持 Web Locks 的现代浏览器。')
 return navigator.locks.request(key(owner,goodsId),async()=>{
  if(user.value?.userId!==owner)throw new Error('登录身份已变化，请重新确认。')
  if(pending(goodsId))throw new Error('请先核对原购买，不能创建新的购买编号。')
  const p={userId:owner,goodsId,confirmationId,purchaseIntentId:crypto.randomUUID()}
  localStorage.setItem(key(owner,goodsId),JSON.stringify(p))
  try{return await retry(p)}catch(e){
   // A definite rejection of this first submission allows a fresh confirmation.
   // Unknown/5xx outcomes retain the original intent. DB purchase guards still arbitrate concurrent tabs.
   if(e instanceof ApiError && [400,404,409].includes(e.status) && !['IDEMPOTENCY_CONFLICT'].includes(e.code))clear(p)
   throw e
  }
 })
}
async function bounded<T>(work:Promise<T>):Promise<T>{let timer:ReturnType<typeof setTimeout>|undefined;try{return await Promise.race([work,new Promise<never>((_,reject)=>{timer=setTimeout(()=>reject(new Error('暂未取得购买结果，请核对原购买编号。')),25000)})])}finally{if(timer)clearTimeout(timer)}}
function clear(p:PendingPurchase){if(user.value?.userId===p.userId&&pending(p.goodsId)?.purchaseIntentId===p.purchaseIntentId)localStorage.removeItem(key(p.userId,p.goodsId))}
export async function retry(p:PendingPurchase){
 const order=await bounded(write<Order>('/orders','POST',{purchaseIntentId:p.purchaseIntentId,confirmationId:p.confirmationId},p.userId))
 clear(p);return order
}
export async function recover(p:PendingPurchase){
 const order=await bounded(request<Order>('/orders/by-intent/'+encodeURIComponent(p.purchaseIntentId),p.userId))
 clear(p);return order
}
export function orderError(e:unknown){
 if(e instanceof ApiError){const text:Record<string,string>={ACTIVE_PURCHASE_EXISTS:'你已有一笔该商品的未结束购买，请查看原订单。',CONFIRMATION_EXPIRED:'报价确认已过期，请重新试算并确认。',CONFIRMATION_ALREADY_USED:'该报价已绑定购买，请核对原订单。',OFFER_CHANGED:'报价或活动已变化，请重新试算后确认。',CANCEL_NOT_ALLOWED:'当前订单需要核对或已开放支付，不能按未支付订单取消。',COORDINATION_VERSION_CONFLICT:'任务状态已变化，请刷新核对后重新选择操作。',COORDINATION_ACTION_NOT_ALLOWED:'当前任务不允许该动作，请刷新核对；证据矛盾不能通过页面恢复。',TEAM_NOT_JOINABLE:'团队已满或暂不可加入，请重新查看团队，不会自动改成开团。',TEAM_NOT_FOUND:'团队不存在或不可访问。',TEAM_OFFER_MISMATCH:'当前报价与该团队活动不一致，请重新试算并核对团队。',OFFER_UNAVAILABLE:'当前没有可参与的优惠。',STOCK_INSUFFICIENT:'库存不足，未建立订单。',ORDER_NOT_FOUND:'暂未查到原购买；请保留原编号继续核对，勿重复下单。',PRODUCT_NOT_SALEABLE:'商品已下架。',IDEMPOTENCY_CONFLICT:'购买编号与原参数不一致，请核对原购买。'};if(text[e.code])return text[e.code]+'（请求编号 '+e.requestId+'）'}
 return explain(e)
}
