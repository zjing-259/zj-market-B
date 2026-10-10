import {request,write,user} from './auth'
import type {OrderPayment,PaymentOperation,PaymentReceipt,PendingPayment} from '../types/payment'
const key=(owner:string,order:string)=>`b-payment:${owner}:${order}`
export function pendingPayment(owner:string,order:string):PendingPayment|null{
 const raw=localStorage.getItem(key(owner,order));if(!raw)return null
 try{const p:PendingPayment=JSON.parse(raw),valid=(s:unknown)=>typeof s==='string'&&/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(s);if(p.owner===owner&&p.orderId===order&&p.body&&valid(p.body.operationId)){
 const keys=Object.keys(p.body).sort().join(',');
 if('previousAttemptId' in p.body&&keys==='operationId,previousAttemptId'&&(p.body.previousAttemptId===null||valid(p.body.previousAttemptId))&&p.path===`/orders/${encodeURIComponent(order)}/payment-attempts`)return p
 if('result' in p.body&&keys==='operationId,result'&&['SUCCEEDED','FAILED'].includes(p.body.result)&&/^\/payments\/[A-Za-z0-9][A-Za-z0-9_-]{0,63}\/attempts\/[A-Za-z0-9][A-Za-z0-9_-]{0,63}\/simulated-results$/.test(p.path))return p
 }}catch{/* Keep corrupt storage until explicitly investigated. */}
 throw new Error('原支付操作记录无法读取，请保留记录并联系维护人员。')
}
export function getPayment(owner:string,order:string){return request<OrderPayment>(`/orders/${encodeURIComponent(order)}/payment`,owner)}
export async function paymentOperation(p:PendingPayment){
 const op=await request<PaymentOperation>(`/orders/${encodeURIComponent(p.orderId)}/payment-operations/${encodeURIComponent(p.body.operationId)}`,p.owner)
 if(['APPLIED','REJECTED'].includes(op.progress)&&user.value?.userId===p.owner&&pendingPayment(p.owner,p.orderId)?.body.operationId===p.body.operationId)localStorage.removeItem(key(p.owner,p.orderId))
 return op
}
export function retryPayment(p:PendingPayment){return write<PaymentReceipt>(p.path,'POST',p.body,p.owner)}
async function start(owner:string,orderId:string,path:string,body:PendingPayment['body']){
 if(!navigator.locks)throw new Error('请使用支持 Web Locks 的现代浏览器。')
 return navigator.locks.request(key(owner,orderId),async()=>{
  if(user.value?.userId!==owner)throw new Error('登录身份已变化，请重新核对。')
  if(pendingPayment(owner,orderId))throw new Error('请先核对原支付操作。')
  const p={owner,orderId,path,body};localStorage.setItem(key(owner,orderId),JSON.stringify(p));return retryPayment(p)
 })
}
export function createAttempt(owner:string,order:string,previousAttemptId:string|null){return start(owner,order,`/orders/${encodeURIComponent(order)}/payment-attempts`,{operationId:crypto.randomUUID(),previousAttemptId})}
export function chooseResult(owner:string,order:string,payment:string,attempt:string,result:'SUCCEEDED'|'FAILED'){return start(owner,order,`/payments/${encodeURIComponent(payment)}/attempts/${encodeURIComponent(attempt)}/simulated-results`,{operationId:crypto.randomUUID(),result})}
