<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { request, user, explain } from '../services/auth'
import { pendingInventory, lastInventoryResult, loadPendingInventory, submitInventory, queryInventoryOperation, retryInventory } from '../services/inventory'
import type { Inventory, InventoryPage, PendingInventory, Ledger } from '../types/inventory'
const listing=ref<InventoryPage>({items:[],page:1,size:20,total:0}), selected=ref<Inventory|null>(null)
const kind=ref<'INBOUND'|'ADJUST'>('INBOUND'),delta=ref(''),reason=ref(''),error=ref(''),busy=ref(false)
const ledger=ref<{items:Ledger[];page:number;size:number;total:number}>({items:[],page:1,size:20,total:0})
const goodsFilter=ref('')
const resultText=computed(() => ({INVENTORY_VERSION_CONFLICT:'库存版本已变化，请刷新并重新确认新操作。',STOCK_INSUFFICIENT:'减少量超过可用库存。',INVENTORY_QUANTITY_OVERFLOW:'库存数量超过允许范围。',INVENTORY_VERSION_EXHAUSTED:'库存版本达到上限，请联系维护人员。','0000':'操作已完成。'}[lastInventoryResult.value?.code ?? ''] ?? '请核对操作结果。'))
const blocked=computed(() => !!selected.value && pendingInventory.value.some(p => p.request.goodsId===selected.value?.goodsId))
let timer:ReturnType<typeof setInterval>|undefined, deadline=0, querying=false
async function load(page=listing.value.page) {
  const uid=user.value?.userId;if(!uid)return
  try { const value=await request<InventoryPage>('/admin/inventory?page='+page+'&size=20'+(goodsFilter.value?'&goodsId='+encodeURIComponent(goodsFilter.value):''),uid);if(user.value?.userId===uid)listing.value=value }
  catch(e){if(user.value?.userId===uid)error.value=explain(e)}
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
onUnmounted(() => {if(timer)clearInterval(timer);window.removeEventListener('storage',storage);document.removeEventListener('visibilitychange',visible)})
</script>
<template>
<section class="catalog" aria-label="库存管理">
 <h1>库存管理</h1><p>下架商品也可备货、盘点；库存维护不会自动上架。</p>
 <p v-if="error" role="alert" class="message error">{{ error }}</p>
 <p v-if="lastInventoryResult" role="status">原操作 {{ lastInventoryResult.operationId }}：{{ lastInventoryResult.outcome==='SUCCEEDED'?'已成功':'已拒绝' }} · {{ resultText }}。下方展示重新读取的当前库存。</p>
 <aside v-if="pendingInventory.length" aria-label="待核对库存操作"><h2>待核对操作</h2><p>结果尚未确认，同商品暂不能新操作。关闭浏览器后仍可恢复；最多自动核对5分钟，之后可手动查询。</p>
 <article v-for="p in pendingInventory" :key="p.operationId"><p>商品 {{ p.request.goodsId }} · {{ p.request.kind==='INBOUND'?'入库':'调整' }} {{ p.request.delta }} · 编号 {{ p.operationId }}</p><button :disabled="busy" @click="recover(p)">查询原结果</button><button :disabled="busy" @click="recover(p,true)">重试原操作</button></article></aside>
 <label>按商品编号查询<input v-model="goodsFilter" name="inventorySearch"></label><button @click="load(1)">查询库存</button><button class="secondary compact" @click="load()">刷新库存</button>
 <table><thead><tr><th>商品编号</th><th>可用</th><th>预留</th><th>已售</th><th>版本</th><th>操作</th></tr></thead><tbody><tr v-for="a in listing.items" :key="a.goodsId"><td>{{ a.goodsId }}</td><td>{{ a.available }}</td><td>{{ a.reserved }}</td><td>{{ a.sold }}</td><td>{{ a.version }}</td><td><button @click="select(a)">维护库存</button></td></tr></tbody></table>
 <div class="pagination"><button :disabled="listing.page<=1" @click="load(listing.page-1)">上一页</button><span>第 {{ listing.page }} 页 · 共 {{ listing.total }} 件</span><button :disabled="listing.page*listing.size>=listing.total" @click="load(listing.page+1)">下一页</button></div>
 <section v-if="selected"><h2>商品 {{ selected.goodsId }}</h2><p>当前可用 {{ selected.available }} · 预留 {{ selected.reserved }} · 已售 {{ selected.sold }} · 版本 {{ selected.version }}</p>
 <form @submit.prevent="submit"><label>操作<select v-model="kind" :disabled="busy || blocked"><option value="INBOUND">入库</option><option value="ADJUST">增减量调整</option></select></label><label>{{ kind==='INBOUND'?'入库数量':'增减量（减少填负数）' }}<input v-model="delta" name="inventoryDelta" required :disabled="busy || blocked" inputmode="text"></label><label>原因<input v-model="reason" name="inventoryReason" required maxlength="256" :disabled="busy || blocked"></label><button type="submit" :disabled="busy || blocked">{{ blocked?'先核对原操作':'确认提交' }}</button></form>
 <button @click="refreshSelected()">刷新当前余额和流水</button>
 <h3>最近库存流水</h3><table><thead><tr><th>时间</th><th>操作者</th><th>类型</th><th>增减</th><th>变化前→后</th><th>原因</th></tr></thead><tbody><tr v-for="l in ledger.items" :key="l.ledgerId"><td>{{ l.createdAt }}</td><td>{{ l.actorId }}</td><td>{{ l.kind }}</td><td>{{ l.delta.available }}</td><td>{{ l.before.available }} → {{ l.after.available }}</td><td>{{ l.reason }}</td></tr></tbody></table>
 </section>
</section>
</template>
