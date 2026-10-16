<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import type { Product, Trial } from '../types/product'
import type { Confirmation, Order, PendingPurchase } from '../types/order'
import { ApiError } from '../errors/ApiError'
import { user, request } from '../services/auth'
import { confirm, submit, recover, retry, pending, orderError } from '../services/orders'
const props=defineProps<{product:Product;trial:Trial|null;teamId?:string;joinable?:boolean}>()
const emit=defineEmits<{ activity: [active: boolean] }>()
const enabled=ref(true),latestPrice=ref('')
const confirmation=ref<Confirmation|null>(null),order=ref<Order|null>(null),unresolved=ref<PendingPurchase|null>(null),busy=ref(false),error=ref('')
let sequence=0,timer:ReturnType<typeof setTimeout>|undefined,deadline=0
function stop(){if(timer)clearTimeout(timer);timer=undefined}
function schedule(){stop();if(!unresolved.value||document.hidden||Date.now()>=deadline)return;timer=setTimeout(()=>void lookup(),3000)}
async function lookup(){const p=unresolved.value;if(!p||busy.value)return;const seq=sequence;busy.value=true;try{const o=await recover(p);if(seq===sequence){order.value=o;unresolved.value=null;error.value=''}}catch(e){if(seq===sequence)error.value=orderError(e)}finally{if(seq===sequence){busy.value=false;schedule()}}}
async function reset(){stop();const seq=++sequence;enabled.value=true;confirmation.value=null;order.value=null;error.value='';latestPrice.value='';busy.value=false;unresolved.value=pending(props.product.goodsId);deadline=Date.now()+300000;if(!user.value)return;if(unresolved.value){void lookup();return}const owner=user.value.userId;try{const o=await request<Order|null>('/products/'+props.product.goodsId+'/active-order',owner);if(seq===sequence)order.value=o}catch(e){if(seq===sequence){if(e instanceof ApiError&&e.code==='RESOURCE_NOT_FOUND')enabled.value=false;else error.value=orderError(e)}}}
async function prepare(){if(!user.value||!props.trial?.offer||busy.value)return;const owner=user.value.userId,seq=sequence;busy.value=true;error.value='';try{const active=await request<Order|null>('/products/'+props.product.goodsId+'/active-order',owner);if(seq!==sequence)return;if(active){order.value=active;return}const c=await confirm(props.product.goodsId,props.trial.offer,owner,props.teamId);if(seq===sequence)confirmation.value=c}catch(e){if(seq===sequence){error.value=orderError(e);if(e instanceof ApiError&&e.code==='OFFER_CHANGED'&&e.data&&typeof e.data==='object'){const value=(e.data as {latestOffer?:{payPrice?:unknown}}).latestOffer?.payPrice;if(typeof value==='string'&&/^(?:0\.(?:0[1-9]|[1-9][0-9])|[1-9][0-9]{0,5}\.[0-9]{2})$/.test(value))latestPrice.value=value}}}finally{if(seq===sequence)busy.value=false}}
async function purchase(original=false){const owner=user.value?.userId;if(!owner||busy.value)return;const seq=sequence;busy.value=true;error.value='';try{const o=original&&unresolved.value?await retry(unresolved.value):await submit(props.product.goodsId,confirmation.value!.confirmationId,owner);if(seq===sequence){order.value=o;unresolved.value=null;confirmation.value=null}}catch(e){if(seq===sequence){error.value=orderError(e);unresolved.value=pending(props.product.goodsId);if(!unresolved.value)confirmation.value=null;deadline=Date.now()+300000}}finally{if(seq===sequence){busy.value=false;schedule()}}}
function visibility(){if(document.hidden)stop();else if(unresolved.value&&Date.now()<deadline)void lookup()}
watch(()=>[user.value?.userId,props.product.goodsId,props.product.productVersion,props.teamId],()=>void reset())
watch(()=>props.trial,()=>void reset())
watch([confirmation,unresolved,busy],()=>emit('activity',!!confirmation.value||!!unresolved.value||busy.value),{immediate:true})
onMounted(()=>{document.addEventListener('visibilitychange',visibility);void reset()})
onUnmounted(()=>{sequence++;stop();document.removeEventListener('visibilitychange',visibility)})
</script>
<template><section v-if="user&&enabled" class="trial-panel" aria-label="购买确认"><h3>我的购买</h3>
<p v-if="error" role="alert">{{error}}</p><p v-if="latestPrice">最新试算金额 ¥ {{latestPrice}}。请先重新试算，再核对并确认；原购买条件未被自动修改。</p>
<template v-if="order"><p>订单 {{order.orderId}} · {{order.status==='PROCESSING'?'处理中':order.status}}</p><p>已按确认条件受理，请在我的订单中查看进度。</p><a :href="'/orders/'+order.orderId">查看原订单</a></template>
<template v-else-if="unresolved"><p>购买结果待核对 · {{unresolved.purchaseIntentId}}</p><button :disabled="busy" @click="lookup">查询原购买</button><button :disabled="busy" @click="purchase(true)">用原编号重试</button></template>
<template v-else-if="confirmation"><p>确认{{teamId?'加入此团队':'开团'}}：¥ {{confirmation.offer.payPrice}}，{{confirmation.offer.targetCount}} 人成团；数量 1。</p><p>报价确认有效至 {{new Date(confirmation.expiresAt).toLocaleTimeString()}}，下单仍会重新核验。</p><button :disabled="busy" @click="purchase()">确认购买</button><button :disabled="busy" @click="confirmation=null">返回</button></template>
<button v-else :disabled="busy||product.availability!=='IN_STOCK'||!product.syncReady||trial?.state!=='AVAILABLE'||(!!teamId&&!joinable)" @click="prepare">核对{{teamId?'参团':'开团'}}报价</button>
</section></template>
