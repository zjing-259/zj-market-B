<script setup lang="ts">
import {computed,onMounted,onUnmounted,ref,watch} from 'vue'
import {user,explain} from '../services/auth'
import {getPayment,pendingPayment,paymentOperation,retryPayment,createAttempt,chooseResult} from '../services/payments'
import type {OrderPayment,PendingPayment,PaymentOperation} from '../types/payment'
const order=location.pathname.split('/')[2]??'',view=ref<OrderPayment|null>(null),pending=ref<PendingPayment|null>(null),operation=ref<PaymentOperation|null>(null),busy=ref(false),error=ref(''),stopped=ref(false)
const active=computed(()=>view.value?.payment?.attempts.find(a=>a.attemptId===view.value?.payment?.activeAttemptId))
const progressLabels:Record<string,string>={PENDING:'正在处理',APPLIED:'已处理',REJECTED:'未受理',WAITING_DEPENDENCY:'正在核对',REVIEW_REQUIRED:'需要后台核对'}
const acceptance:Record<string,string>={NOT_SENT:'营销确认尚未发送',PENDING:'已支付，营销确认中',ACCEPTED:'已支付，营销已确认，等待成团处理',REJECTED:'已支付，营销未接受，等待退款处理',REVIEW_REQUIRED:'资金需要后台核对'}
const labels:Record<string,string>={CREATING:'正在创建',OPEN:'等待选择模拟结果',UNKNOWN:'结果待核对',FAILED:'本次尝试失败，可重新尝试',SUCCEEDED:'渠道已成功，等待商城同步',CLOSED_UNPAID:'渠道已确认未付关闭'}
let generation=0,timer:ReturnType<typeof setTimeout>|undefined,until=Date.now()+300000
function stop(){if(timer)clearTimeout(timer);timer=undefined}
function schedule(){stop();if(document.hidden||Date.now()>=until||!user.value){stopped.value=Date.now()>=until;return}if(pending.value||active.value?.state==='CREATING'||active.value?.state==='UNKNOWN'||view.value?.payment?.fundsState==='UNKNOWN'||view.value?.payment?.fundsState==='SUCCEEDED'&&view.value.payment.aAcceptance==='PENDING')timer=setTimeout(()=>void load(),2000)}
async function load(){if(!user.value||busy.value)return;const owner=user.value.userId,seq=generation;busy.value=true;error.value='';try{
 const p=pendingPayment(owner,order);if(seq===generation)pending.value=p
 if(p){try{const op=await paymentOperation(p);if(seq===generation){operation.value=op;pending.value=pendingPayment(owner,order)}}catch(e){if(seq===generation)error.value=explain(e)+' 原操作编号已保留，可查询或重试原操作。'}}
 const next=await getPayment(owner,order);if(seq===generation)view.value=next
 }catch(e){if(seq===generation)error.value=explain(e)}finally{if(seq===generation){busy.value=false;schedule()}}}
async function act(action:'CREATE'|'SUCCEEDED'|'FAILED'|'RETRY'){
 if(!user.value||busy.value)return;const owner=user.value.userId,seq=generation;busy.value=true;error.value=''
 try{if(action==='RETRY'&&pending.value)await retryPayment(pending.value);else if(action==='CREATE')await createAttempt(owner,order,active.value?.attemptId??null);else if(active.value&&view.value?.payment&&action!=='RETRY')await chooseResult(owner,order,view.value.payment.paymentId,active.value.attemptId,action)}catch(e){if(seq===generation)error.value=explain(e)}finally{if(seq===generation){busy.value=false;try{pending.value=pendingPayment(owner,order)}catch(e){error.value=explain(e)}until=Date.now()+300000;const previous=error.value;await load();if(previous)error.value=previous}}
}
function visible(){if(document.hidden)stop();else if(Date.now()<until)void load()}
watch(()=>user.value?.userId,()=>{generation++;stop();view.value=null;pending.value=null;operation.value=null;error.value='';busy.value=false;until=Date.now()+300000;void load()})
onMounted(()=>{document.addEventListener('visibilitychange',visible);void load()})
onUnmounted(()=>{generation++;stop();document.removeEventListener('visibilitychange',visible)})
</script>
<template><section class="payment-page"><p class="eyebrow">模拟收银台</p><h1>模拟支付，不产生真实扣款</h1><p>订单 {{order}}</p>
<p v-if="!user">请登录后查看本人收银台。<a :href="'/login?returnTo='+encodeURIComponent('/orders/'+order+'/payment')">去登录</a></p>
<template v-else><button :disabled="busy" @click="until=Date.now()+300000;load()">查询支付状态</button><p v-if="error" role="alert">{{error}}</p><p v-if="stopped">自动查询已结束，可手动查询。</p>
<template v-if="view"><template v-if="view.payment"><h2>¥ {{view.payment.amount}} CNY</h2><p>支付单 {{view.payment.paymentId}}</p><p>付款截止：{{new Date(view.payment.paymentDeadline).toLocaleString()}}</p><p v-if="active" role="status">{{active.state==='SUCCEEDED'&&view.payment.fundsState==='SUCCEEDED'?'模拟支付已成功':labels[active.state]}}</p><p v-if="active?.paidAt">渠道成功时间：{{new Date(active.paidAt).toLocaleString()}}</p><p v-if="view.payment.fundsState==='UNKNOWN'">资金结果仍待商城核对，请保留原订单与支付编号。</p><p v-if="view.payment.fundsState==='SUCCEEDED'" role="status">{{acceptance[view.payment.aAcceptance]}}</p><p v-if="view.payment.reviewRequired" role="alert">需要后台核对，暂不能操作。</p>
<div v-if="!pending&&active?.canSelectResult"><button :disabled="busy" @click="act('SUCCEEDED')">选择模拟成功</button><button class="secondary" :disabled="busy" @click="act('FAILED')">选择模拟失败</button></div>
<details><summary>最近的渠道尝试</summary><p v-for="a in view.payment.attempts" :key="a.attemptId">第 {{a.attemptNo}} 次 · {{a.state==='SUCCEEDED'?'渠道已成功':labels[a.state]}} · {{a.attemptId}}</p></details></template>
<p v-else>尚未创建支付单。</p><button v-if="!pending&&view.canCreateAttempt" :disabled="busy" @click="act('CREATE')">{{active?.state==='FAILED'?'重新尝试模拟支付':'创建模拟支付尝试'}}</button>
<p v-if="!view.canCreateAttempt&&!view.payment">当前订单暂不可支付。</p></template>
<div v-if="pending"><p>原操作编号：{{pending.body.operationId}} · {{operation?progressLabels[operation.progress]:'结果待查询'}}</p><p>查询暂未找到记录也不能确认写入失败，请保留原编号。</p><button :disabled="busy" @click="act('RETRY')">重试原操作</button></div></template><p><a :href="'/orders/'+order">返回订单</a></p></section></template>
