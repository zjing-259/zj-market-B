<script setup lang="ts">
import {onMounted,onUnmounted,ref,watch} from 'vue'
import {user,request,publicGet,write,explain} from '../services/auth'
import type {Team} from '../types/order'
import type {Product,Trial} from '../types/product'
import PurchasePanel from './PurchasePanel.vue'
const team=ref<Team|null>(null),product=ref<Product|null>(null),trial=ref<Trial|null>(null),error=ref(''),busy=ref(false)
const origin=location.origin
let id=''
try{id=decodeURIComponent(location.pathname.split('/')[2]??'')}catch{id=''}
let sequence=0
async function load(){const owner=user.value?.userId;if(!owner||busy.value)return;if(!id){error.value='团队链接无效，请重新选择团队。';return}const seq=++sequence;busy.value=true;error.value='';trial.value=null;team.value=null;product.value=null;try{const t=await request<Team>('/teams/'+encodeURIComponent(id),owner);if(seq!==sequence)return;team.value=t;const p=await publicGet<Product>('/products/'+encodeURIComponent(t.goodsId));if(seq!==sequence)return;product.value=p;if(p.syncReady){const quote=await write<Trial>('/products/'+encodeURIComponent(t.goodsId)+'/trial','POST',{},owner);if(seq!==sequence)return;trial.value=quote;if(quote.offer&&(quote.offer.activityId!==t.activityId||quote.offer.targetCount!==t.targetCount)){trial.value=null;error.value='当前活动或成团条件与此团队不一致，请重新核对；不会自动改成开团。'}}}catch(e){if(seq===sequence)error.value=explain(e)}finally{if(seq===sequence)busy.value=false}}
watch(()=>user.value?.userId,()=>{sequence++;busy.value=false;team.value=null;product.value=null;trial.value=null;void load()})
onMounted(()=>void load());onUnmounted(()=>sequence++)
</script>
<template><section><h1>分享团队</h1><p v-if="!user">请登录后查看团队详情。<a :href="'/login?returnTo='+encodeURIComponent('/teams/'+encodeURIComponent(id))">去登录</a></p><template v-else><button :disabled="busy" @click="load">刷新团队并重新试算</button><p v-if="error" role="alert">{{error}}</p><article v-if="team"><h2>团队 {{team.teamId}}</h2><p>{{team.status}} · {{team.targetCount}} 人成团 · 已占 {{team.reservedCount}} 位 · 已支付 {{team.paidCount}} 位</p><p>有效至 {{new Date(team.validEndTime).toLocaleString()}}</p><p>分享地址：<a :href="'/teams/'+encodeURIComponent(team.teamId)">{{origin}}/teams/{{team.teamId}}</a></p><p v-if="!team.joinable">团队当前不可加入，不会改为新开团。</p><a v-if="team.myOrderId" :href="'/orders/'+team.myOrderId">查看我的原订单</a><template v-if="product"><h2>{{product.goodsName}}</h2><p>{{product.availability==='IN_STOCK'?'有货':'缺货'}}</p><p v-if="trial?.offer">当前试算 ¥ {{trial.offer.payPrice}}；提交时仍重新核验。</p><PurchasePanel :product="product" :trial="trial" :team-id="team.teamId" :joinable="team.joinable" /></template></article></template></section></template>
