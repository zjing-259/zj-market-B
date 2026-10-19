import {request,write,user} from './auth'
import type {OrderPayment,PaymentOperation,PaymentReceipt,PendingPayment} from '../types/payment'
const key=(owner:string,order:string)=>`b-payment:${owner}:${order}`
const flowKey=(owner:string,order:string)=>`b-payment-flow:${owner}:${order}`
export interface PaymentFlow { owner:string;orderId:string;result:'SUCCEEDED'|'FAILED';attemptId:string|null;phase:'PREPARE'|'RESULT_SENT' }
export function paymentFlow(owner:string,order:string):PaymentFlow|null{
 const raw=localStorage.getItem(flowKey(owner,order));if(!raw)return null
 try{const flow:PaymentFlow=JSON.parse(raw);if(flow.owner===owner&&flow.orderId===order&&['SUCCEEDED','FAILED'].includes(flow.result)&&
  ['PREPARE','RESULT_SENT'].includes(flow.phase)&&
  (flow.attemptId===null||typeof flow.attemptId==='string'&&/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(flow.attemptId)))return flow}catch{/* Preserve damaged record for support. */}
 throw new Error('原模拟支付选择无法读取，请保留本机记录并联系维护人员。')
}
export function savePaymentFlow(flow:PaymentFlow){if(user.value?.userId!==flow.owner)throw new Error('登录身份已变化，请重新核对。');localStorage.setItem(flowKey(flow.owner,flow.orderId),JSON.stringify(flow))}
export function clearPaymentFlow(flow:PaymentFlow){const current=paymentFlow(flow.owner,flow.orderId);if(user.value?.userId===flow.owner&&current?.result===flow.result&&current.phase===flow.phase&&current.attemptId===flow.attemptId)localStorage.removeItem(flowKey(flow.owner,flow.orderId))}
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
export function retryPayment(p:PendingPayment){
 if(!navigator.locks)throw new Error('请使用支持 Web Locks 的现代浏览器。')
 return navigator.locks.request(key(p.owner,p.orderId),async()=>{
  if(user.value?.userId!==p.owner||pendingPayment(p.owner,p.orderId)?.body.operationId!==p.body.operationId)throw new Error('原支付操作已变化，请重新核对。')
  return write<PaymentReceipt>(p.path,'POST',p.body,p.owner)
 })
}
async function start(owner:string,orderId:string,path:string,body:PendingPayment['body']){
 if(!navigator.locks)throw new Error('请使用支持 Web Locks 的现代浏览器。')
 return navigator.locks.request(key(owner,orderId),async()=>{
  if(user.value?.userId!==owner)throw new Error('登录身份已变化，请重新核对。')
  if(pendingPayment(owner,orderId))throw new Error('请先核对原支付操作。')
  const p={owner,orderId,path,body};localStorage.setItem(key(owner,orderId),JSON.stringify(p));return write<PaymentReceipt>(p.path,'POST',p.body,p.owner)
 })
}
export function createAttempt(owner:string,order:string,previousAttemptId:string|null){return start(owner,order,`/orders/${encodeURIComponent(order)}/payment-attempts`,{operationId:crypto.randomUUID(),previousAttemptId})}
export function chooseResult(owner:string,order:string,payment:string,attempt:string,result:'SUCCEEDED'|'FAILED'){return start(owner,order,`/payments/${encodeURIComponent(payment)}/attempts/${encodeURIComponent(attempt)}/simulated-results`,{operationId:crypto.randomUUID(),result})}
