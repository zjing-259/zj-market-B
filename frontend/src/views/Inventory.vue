<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { request, user, explain } from '../services/auth'
import { pendingInventory, lastInventoryResult, loadPendingInventory, submitInventory, queryInventoryOperation, retryInventory } from '../services/inventory'
import type { Inventory, InventoryPage, PendingInventory, Ledger } from '../types/inventory'
import TableScroll from '../components/TableScroll.vue'
const listing=ref<InventoryPage>({items:[],page:1,size:20,total:0}), selected=ref<Inventory|null>(null)
const kind=ref<'INBOUND'|'ADJUST'>('INBOUND'),delta=ref(''),reason=ref(''),error=ref(''),busy=ref(false)
const ledger=ref<{items:Ledger[];page:number;size:number;total:number}>({items:[],page:1,size:20,total:0})
const goodsFilter=ref('')
const loading=ref(false)
let loadSequence=0
const resultText=computed(() => ({INVENTORY_VERSION_CONFLICT:'库存版本已变化，请刷新并重新确认新操作。',STOCK_INSUFFICIENT:'减少量超过可用库存。',INVENTORY_QUANTITY_OVERFLOW:'库存数量超过允许范围。',INVENTORY_VERSION_EXHAUSTED:'库存版本达到上限，请联系维护人员。','0000':'操作已完成。'}[lastInventoryResult.value?.code ?? ''] ?? '请核对操作结果。'))
const blocked=computed(() => !!selected.value && pendingInventory.value.some(p => p.request.goodsId===selected.value?.goodsId))
let timer:ReturnType<typeof setInterval>|undefined, deadline=0, querying=false
async function load(page=listing.value.page) {
  const uid=user.value?.userId;if(!uid)return
  const seq=++loadSequence;loading.value=true;error.value=''
  try { const value=await request<InventoryPage>('/admin/inventory?page='+page+'&size=20'+(goodsFilter.value?'&goodsId='+encodeURIComponent(goodsFilter.value.trim()):''),uid);if(seq===loadSequence&&user.value?.userId===uid)listing.value=value }
  catch(e){if(seq===loadSequence&&user.value?.userId===uid)error.value=explain(e)}
  finally{if(seq===loadSequence)loading.value=false}
}
async function select(a:Inventory) {selected.value=a;delta.value='';reason.value='';await refreshSelected()}
async function refreshSelected() {
  const id=selected.value?.goodsId,uid=user.value?.userId;if(!id||!uid)return
  try {
    const [a,l]=await Promise.all([request<Inventory>('/admin/inventory/'+id,uid),request<typeof ledger.value>('/admin/inventory/'+id+'/ledger',uid)])
    if(user.value?.userId===uid && selected.value?.goodsId===id){selected.value=a;ledger.value=l}
  }catch(e){if(user.value?.userId===uid)error.value=explain(e)}
}
async function submit() {
  if(!selected.value || busy.value || blocked.value)return
  busy.value=true;error.value=''
  try { await submitInventory({kind:kind.value,goodsId:selected.value.goodsId,delta:delta.value,expectedVersion:selected.value.version,reason:reason.value});await refreshSelected();await load() }
  catch(e){error.value=explain(e)}finally{busy.value=false;deadline=Date.now()+300000}
}
async function recover(p:PendingInventory,retry=false) {
  if(busy.value)return;busy.value=true;error.value=''
  try {if(retry)await retryInventory(p);else await queryInventoryOperation(p);await refreshSelected();await load()}
  catch(e){error.value=explain(e)}finally{busy.value=false}
}
async function poll() {
  if(document.hidden || querying || busy.value || Date.now()>deadline || !user.value?.roles.includes('OPERATOR'))return
  querying=true
  try{loadPendingInventory();for(const p of [...pendingInventory.value]){try{await queryInventoryOperation(p)}catch{/* Keep pending; manual actions remain visible. */}}}
  catch(e){error.value=explain(e)}finally{querying=false}
}
function storage(){try{loadPendingInventory();void poll()}catch(e){error.value=explain(e)}}
function visible(){if(!document.hidden){deadline=Date.now()+300000;void poll()}}
watch(() => user.value?.userId,() => {selected.value=null;listing.value.items=[];ledger.value.items=[];error.value='';deadline=Date.now()+300000;storage();void load()})
watch(lastInventoryResult,() => {void refreshSelected();void load()})
onMounted(() => {deadline=Date.now()+300000;storage();void load();timer=setInterval(poll,3000);window.addEventListener('storage',storage);document.addEventListener('visibilitychange',visible)})
onUnmounted(() => {loadSequence++;if(timer)clearInterval(timer);window.removeEventListener('storage',storage);document.removeEventListener('visibilitychange',visible)})
</script>
<template>
<section class="catalog" aria-label="库存管理">
 <p class="eyebrow">正经商城 · 运营工作台</p><h1>库存管理</h1><p class="muted">下架商品也可备货、盘点；库存维护不会自动上架。</p>
 <p v-if="error" role="alert" class="message error">{{ error }}</p>
 <p v-if="lastInventoryResult" role="status">{{ lastInventoryResult.outcome==='SUCCEEDED'?'库存操作已完成':'库存操作未生效' }} · {{ resultText }} 下方展示重新读取的当前库存。</p>
 <aside v-if="pendingInventory.length" aria-label="待核对库存操作"><h2>待核对操作</h2><p>结果尚未确认，同商品暂不能新操作。关闭浏览器后仍可恢复；最多自动核对5分钟，之后可手动查询。</p>
 <article v-for="p in pendingInventory" :key="p.operationId"><p>{{ p.request.kind==='INBOUND'?'入库':'调整' }} {{ p.request.delta }} · 结果待核对</p><details><summary>原操作信息</summary><p>商品 {{ p.request.goodsId }} · 编号 {{ p.operationId }}</p></details><button :disabled="busy" @click="recover(p)">查询原结果</button><button class="secondary" :disabled="busy" @click="recover(p,true)">重试原操作</button></article></aside>
 <form class="filters" @submit.prevent="load(1)"><label>按商品编号查询<input v-model="goodsFilter" name="inventorySearch" maxlength="64" placeholder="填写商品编号；留空查看全部"></label><button :disabled="loading">查询库存</button><button type="button" class="secondary compact" :disabled="loading" @click="load()">刷新库存</button></form>
 <p v-if="loading" role="status">正在读取库存…</p><p v-if="!loading&&!error&&!listing.items.length" class="empty">暂无匹配库存，请核对商品编号。</p>
 <TableScroll v-if="listing.items.length" label="库存余额，可横向滚动"><table><thead><tr><th scope="col">商品编号</th><th scope="col">可用</th><th scope="col">预留</th><th scope="col">已售</th><th scope="col">版本</th><th scope="col">操作</th></tr></thead><tbody><tr v-for="a in listing.items" :key="a.goodsId"><td>{{ a.goodsId }}</td><td>{{ a.available }}</td><td>{{ a.reserved }}</td><td>{{ a.sold }}</td><td>{{ a.version }}</td><td><button class="secondary" @click="select(a)">维护库存</button></td></tr></tbody></table></TableScroll>
 <div class="pagination"><button :disabled="listing.page<=1" @click="load(listing.page-1)">上一页</button><span>第 {{ listing.page }} 页 · 共 {{ listing.total }} 件</span><button :disabled="listing.page*listing.size>=listing.total" @click="load(listing.page+1)">下一页</button></div>
 <section v-if="selected" class="maintenance-card"><h2>维护当前商品库存</h2><div class="inventory-summary"><span>可用<strong>{{ selected.available }}</strong></span><span>预留<strong>{{ selected.reserved }}</strong></span><span>已售<strong>{{ selected.sold }}</strong></span></div>
 <details class="support-details"><summary>商品与版本信息</summary><p>商品 {{ selected.goodsId }} · 版本 {{ selected.version }}</p><p v-if="lastInventoryResult">最近原操作编号：{{ lastInventoryResult.operationId }}</p></details>
 <form @submit.prevent="submit"><label>操作<select v-model="kind" :disabled="busy || blocked"><option value="INBOUND">入库</option><option value="ADJUST">增减量调整</option></select></label><label>{{ kind==='INBOUND'?'入库数量':'增减量（减少填负数）' }}<input v-model="delta" name="inventoryDelta" required :disabled="busy || blocked" inputmode="text" :placeholder="kind==='INBOUND'?'例如：20':'例如：5 或 -2'" aria-describedby="inventoryQuantityHint"></label><p id="inventoryQuantityHint" class="muted">只接受非零整数；减少量不能超过可用库存，预留与已售数量由交易流程管理。</p><label>原因<input v-model="reason" name="inventoryReason" required maxlength="256" :disabled="busy || blocked" placeholder="例如：到货入库或盘点差额"></label><button type="submit" :disabled="busy || blocked">{{ blocked?'先核对原操作':busy?'提交核对中…':'确认提交' }}</button></form>
 <button @click="refreshSelected()">刷新当前余额和流水</button>
 <details><summary>最近库存流水</summary><p v-if="!ledger.items.length">暂无库存流水。</p><TableScroll v-else label="库存审计流水，可横向滚动"><table><thead><tr><th scope="col">时间</th><th scope="col">操作者</th><th scope="col">类型</th><th scope="col">增减</th><th scope="col">变化前→后</th><th scope="col">原因</th></tr></thead><tbody><tr v-for="l in ledger.items" :key="l.ledgerId"><td>{{ l.createdAt }}</td><td>{{ l.actorId }}</td><td>{{ l.kind }}</td><td>{{ l.delta.available }}</td><td>{{ l.before.available }} → {{ l.after.available }}</td><td>{{ l.reason }}</td></tr></tbody></table></TableScroll></details>
 </section>
</section>
</template>
