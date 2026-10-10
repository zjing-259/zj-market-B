<script setup lang="ts">
import PurchasePanel from './PurchasePanel.vue'
import type { Sync, Quarantine, Product, Trial, Page } from '../types/product'
import { ApiError } from '../errors/ApiError'
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { user, request, publicGet, write, explain } from '../services/auth'
const props = defineProps<{ admin: boolean }>()
const quarantine = ref<{ items: Quarantine[]; page: number; size: number; total: number } | null>(null)
const syncLabels: Record<string, string> = { PENDING: '等待同步', CONFIRMED: '已确认', REJECTED: '营销端拒绝，需核对商品', RECONCILIATION_REQUIRED: '需要核对' }
const syncPanel = ref(false)
const trial = ref<Trial | null>(null), trialBusy = ref(false), trialError = ref('')
let trialSequence = 0, refreshSequence = 0
let refreshTimer: ReturnType<typeof setTimeout> | undefined
const refreshing = ref(false), refreshExpired = ref(false)
let refreshDeadline = 0
function stopRefresh() { ++refreshSequence; if (refreshTimer) clearTimeout(refreshTimer); refreshTimer = undefined }
async function refreshProduct() {
  const p = selected.value; if (!p || props.admin || refreshing.value) return
  const sequence = refreshSequence; refreshing.value = true
  try { const latest = await publicGet<Product>(`/products/${encodeURIComponent(p.goodsId)}`); if (sequence === refreshSequence && selected.value?.goodsId === p.goodsId) selected.value = latest }
  catch (e) { if (sequence === refreshSequence) { trialError.value = explain(e); if (e instanceof ApiError && e.status === 404) { selected.value = null; error.value = explain(e) } } }
  finally { refreshing.value = false }
}
function scheduleRefresh() {
  if (props.admin || !selected.value || selected.value.syncReady) return
  const sequence = refreshSequence
  refreshTimer = setTimeout(async () => {
    if (sequence !== refreshSequence) return
    if (Date.now() >= refreshDeadline) { refreshExpired.value = true; return }
    await refreshProduct()
    if (sequence === refreshSequence) scheduleRefresh()
  }, 3000)
}
const listing = ref<Page>({ items: [], page: 1, size: 20, total: 0 }), selected = ref<Product | null>(null)
const editing = ref(false), busy = ref(false), error = ref(''), notice = ref(''), broken = ref<Record<string, boolean>>({})
const filter = ref(''), goodsName = ref(''), description = ref(''), imageUrl = ref(''), price = ref(''), status = ref('OFF_SALE')
const prefix = () => props.admin ? '/admin/products' : '/products'
const read = <T,>(path: string) => props.admin ? request<T>(path) : publicGet<T>(path)
async function load(page = listing.value.page) {
  busy.value = true; error.value = ''
  try { listing.value = await read<Page>(`${prefix()}?page=${page}&size=20${props.admin && filter.value ? `&saleStatus=${filter.value}` : ''}`) }
  catch (e) { error.value = explain(e) } finally { busy.value = false }
}
function browse(path: string) { history.pushState(null, '', path); window.dispatchEvent(new PopStateEvent('popstate')) }
function detail(p: Product) { browse(`${prefix()}/${encodeURIComponent(p.goodsId)}`) }
function backToList() { if (location.pathname === prefix()) selected.value = null; else browse(prefix()) }

function form(p: Product | null) {
  selected.value = p; goodsName.value = p?.goodsName ?? ''; description.value = p?.description ?? ''; imageUrl.value = p?.imageUrl ?? ''; price.value = p?.originalPrice ?? ''; status.value = p?.saleStatus ?? 'OFF_SALE'
  editing.value = true; error.value = ''; notice.value = ''
}
async function save() {
  if (busy.value) return
  const normalizedName = goodsName.value.trim()
  if (!normalizedName || normalizedName.length > 128) { error.value = '商品名称去掉首尾空白后须为 1～128 个 UTF-16 单元，emoji 通常占 2 个。'; return }
  if (!/^(?:0\.(?:0[1-9]|[1-9][0-9])|[1-9][0-9]{0,5}\.[0-9]{2})$/.test(price.value)) { error.value = '原价须为 0.01～999999.99 元的两位小数。'; return }
  busy.value = true; error.value = ''; notice.value = ''
  const before = selected.value
  const fields = { goodsName: goodsName.value, description: description.value, imageUrl: imageUrl.value || null, originalPrice: price.value, currency: 'CNY', saleStatus: status.value }
  try {
    selected.value = await write<Product>(before ? `/admin/products/${encodeURIComponent(before.goodsId)}` : '/admin/products', before ? 'PUT' : 'POST', before ? { ...fields, expectedVersion: before.productVersion } : fields)
    editing.value = false; notice.value = before?.productVersion === selected.value.productVersion ? '内容没有变化，版本保持不变。' : '商品已保存，营销资料等待同步。'
    await load()
  } catch (e) { error.value = `${explain(e)} 请先重新读取商品核对是否已保存；创建失败时请先查看列表，避免重复创建。` }
  finally { busy.value = false }
}
async function reread() {
  const id = selected.value?.goodsId
  if (!id) { await load(); return }
  busy.value = true; error.value = ''
  try { form(await request<Product>(`/admin/products/${encodeURIComponent(id)}`)); notice.value = '已载入当前版本，请核对内容后再保存。' }
  catch (e) { error.value = explain(e) } finally { busy.value = false }
}
async function syncStatus() {
  const p = selected.value
  if (!p || busy.value) return
  busy.value = true; error.value = ''; notice.value = ''
  try {
    await request<Sync>(`/admin/products/${encodeURIComponent(p.goodsId)}/sync`)
    const latest = await request<Product>(`/admin/products/${encodeURIComponent(p.goodsId)}`)
    if (selected.value?.goodsId === p.goodsId) { selected.value = latest; syncPanel.value = true }
  } catch (e) { error.value = explain(e) } finally { busy.value = false }
}
async function controlSync(action: 'retries' | 'pauses') {
  const p = selected.value
  if (!p?.sync || busy.value) return
  busy.value = true; error.value = ''; notice.value = ''
  try {
    await write(`/admin/products/${encodeURIComponent(p.goodsId)}/sync/${action}`, 'POST', { eventId: p.sync.targetEventId, expectedVersion: p.productVersion })
    selected.value = await request<Product>(`/admin/products/${encodeURIComponent(p.goodsId)}`)
    notice.value = action === 'pauses' ? '已暂停自动同步。' : '原同步记录已恢复，等待营销端确认。'
  } catch (e) { error.value = `${explain(e)} 请重新读取同步状态后核对。` } finally { busy.value = false }
}
async function readQuarantine(page = 1) {
  if (busy.value) return
  busy.value = true; error.value = ''
  try { quarantine.value = await request(`/admin/sync/quarantine?page=${page}&size=20`) }
  catch (e) { error.value = explain(e) } finally { busy.value = false }
}
async function calculateTrial() {
  const p = selected.value, person = user.value?.userId
  if (props.admin || !p || !person || !p.syncReady || p.saleStatus !== 'ON_SALE') return
  const sequence = ++trialSequence
  trial.value = null; trialError.value = ''; trialBusy.value = true
  const current = () => sequence === trialSequence && selected.value?.goodsId === p.goodsId && selected.value.productVersion === p.productVersion && user.value?.userId === person
  try {
    const result = await write<Trial>(`/products/${encodeURIComponent(p.goodsId)}/trial`, 'POST', {})
    if (!current()) return
    const latest = await publicGet<Product>(`/products/${encodeURIComponent(p.goodsId)}`)
    if (!current()) return
    selected.value = latest
    if (result.goodsId !== latest.goodsId || result.productVersion !== latest.productVersion || !latest.syncReady) return
    trial.value = result
  } catch (e) {
    if (!current()) return
    trialError.value = explain(e)
    if (e instanceof ApiError && [404,409].includes(e.status)) {
      try { const latest = await publicGet<Product>(`/products/${encodeURIComponent(p.goodsId)}`); if (current()) selected.value = latest }
      catch { if (current()) { selected.value = null; error.value = '商品不存在或已下架，请返回列表查看其他商品。' } }
    }
  } finally { if (sequence === trialSequence) trialBusy.value = false }
}
watch([() => selected.value?.goodsId, () => selected.value?.productVersion, () => selected.value?.syncReady, () => user.value?.userId], () => {
  ++trialSequence; trial.value = null; trialError.value = ''; trialBusy.value = false
  if (!props.admin && selected.value?.syncReady && user.value) void calculateTrial()
})
watch([() => selected.value?.goodsId, () => selected.value?.productVersion, () => selected.value?.syncReady], () => {
  stopRefresh(); refreshExpired.value = false
  if (!props.admin && selected.value && !selected.value.syncReady) { refreshDeadline = Date.now() + 60000; scheduleRefresh() }
})
onUnmounted(() => { ++trialSequence; stopRefresh() })
onMounted(async () => {
  await load(1)
  const match = location.pathname.match(/^\/(?:admin\/)?products\/([^/]+)$/)
  if (match) {
    busy.value = true
    try { selected.value = await read<Product>(`${prefix()}/${encodeURIComponent(decodeURIComponent(match[1]!))}`) }
    catch (e) { error.value = explain(e) } finally { busy.value = false }
  }
})
</script>
<template>
  <section class="catalog" :aria-label="admin ? '商品管理' : '商城商品'">
    <div class="catalog-heading"><div><p class="eyebrow">{{ admin ? 'PRODUCT MANAGEMENT' : 'ZHIJI COLLECTION' }}</p><h1>{{ admin ? '商品管理' : '在售商品' }}</h1><p class="muted">{{ admin ? '维护商品资料、基础售价及上下架状态。' : '查看商品资料和基础售价。' }}</p></div><button v-if="admin" class="compact" :disabled="busy" @click="form(null)">创建商品</button></div>
    <p v-if="admin && !user?.roles.includes('OPERATOR')" role="alert">当前账号没有运营权限。</p>
    <p v-if="error" role="alert" class="message error">{{ error }}</p><p v-if="notice" role="status" class="message notice">{{ notice }}</p>
    <form v-if="admin && editing" class="product-editor" @submit.prevent="save">
      <h2>{{ selected ? '编辑商品' : '创建商品' }}</h2><p v-if="selected" class="muted">当前编辑版本：{{ selected.productVersion }}</p>
      <label for="goodsName">商品名称</label><input id="goodsName" v-model="goodsName" required :disabled="busy" aria-describedby="goodsNameHint"><small id="goodsNameHint">去掉首尾空白后最多 128 个 UTF-16 单元；普通中文占 1 个，emoji 通常占 2 个。</small>
      <label for="description">商品描述（纯文本）</label><small>请使用纯文本，HTML 标签会被拒绝。</small><textarea id="description" v-model="description" :disabled="busy" rows="4"></textarea>
      <label for="imageUrl">图片 HTTPS 地址（选填）</label><input id="imageUrl" v-model="imageUrl" type="url" :disabled="busy" placeholder="https://…">
      <label for="originalPrice">原价（元）</label><input id="originalPrice" v-model="price" required inputmode="decimal" :disabled="busy" placeholder="99.00">
      <label for="saleStatus">售卖状态</label><select id="saleStatus" v-model="status" :disabled="busy"><option value="OFF_SALE">下架</option><option value="ON_SALE">在售</option></select>
      <div class="actions"><button :disabled="busy" type="submit">保存商品</button><button type="button" class="secondary" :disabled="busy" @click="reread">重新读取</button><button type="button" class="secondary" @click="editing=false">关闭编辑</button></div>
    </form>
    <article v-else-if="selected" class="product-detail">
      <button class="secondary compact" @click="backToList">返回列表</button>
      <img v-if="selected.imageUrl && !broken[selected.goodsId]" :src="selected.imageUrl" :alt="selected.goodsName" referrerpolicy="no-referrer" @error="broken[selected.goodsId]=true"><div v-else class="image-placeholder">商品图片暂无</div>
      <h2>{{ selected.goodsName }}</h2><p v-if="selected.availability">{{ selected.availability==='IN_STOCK'?'有货':'暂时缺货' }}</p><p class="product-price">¥ {{ selected.originalPrice }}</p><p class="product-description">{{ selected.description || '暂无商品描述。' }}</p>
      <p>{{ selected.saleStatus === 'ON_SALE' ? '在售' : '已下架' }} · 商品版本 {{ selected.productVersion }}</p><p v-if="!selected.syncReady" class="muted">资料更新中，暂不可试算</p>
      <section v-if="!admin" class="trial-panel" aria-label="我的优惠">
        <h3>我的优惠</h3>
        <p v-if="!selected.syncReady" class="muted">{{ refreshExpired ? '自动刷新已结束，可手动刷新商品资料。' : '每 3 秒刷新商品资料，最多等待 1 分钟。' }}</p>
        <button class="secondary compact" :disabled="refreshing" @click="refreshProduct">刷新商品资料</button>
        <p v-if="!user">登录后查看适用于你的优惠。<a :href="`/login?returnTo=${encodeURIComponent('/products/'+selected.goodsId)}`">登录查看优惠</a></p>
        <template v-else>
          <p v-if="trialBusy" role="status">正在为你试算优惠…</p>
          <p v-if="trialError" role="alert" class="message error">{{ trialError }}</p>
          <div v-if="trial" aria-live="polite">
            <p v-if="trial.state === 'NO_PUBLIC_OFFER'">暂无可展示优惠。</p>
            <p v-else-if="trial.state === 'INELIGIBLE'">你当前不符合该优惠的参与条件。</p>
            <p v-else>你当前可参与此优惠。</p>
            <dl v-if="trial.offer"><dt>{{ trial.state === 'AVAILABLE' ? '优惠估算价' : '活动参考价' }}</dt><dd class="product-price">¥ {{ trial.offer.payPrice }}</dd><dt>优惠金额</dt><dd>¥ {{ trial.offer.deductionPrice }}</dd><dt>成团人数</dt><dd>{{ trial.offer.targetCount }} 人</dd></dl>
            <small class="muted">本次试算：{{ new Date(trial.quotedAt).toLocaleString('zh-CN') }}。试算不会保留优惠资格或价格。</small>
          </div>
          <button class="secondary compact" :disabled="trialBusy || !selected.syncReady" @click="calculateTrial">重新试算</button>
        </template>
      </section>
      <PurchasePanel v-if="!admin" :key="selected.goodsId" :product="selected" :trial="trial" />
      <p v-if="admin" class="muted">营销同步：{{ syncLabels[selected.sync?.state ?? ''] ?? '等待核对' }} · 目标版本 {{ selected.sync?.targetVersion }}</p><button v-if="admin" class="compact" @click="form(selected)">编辑商品</button>
      <div v-if="admin" class="sync-controls">
        <button class="secondary compact" :disabled="busy" @click="syncStatus">读取同步状态</button>
        <div v-if="syncPanel && selected.sync" aria-label="同步详情">
          <p>当前目标版本 {{ selected.sync.targetVersion }} · 已确认版本 {{ selected.sync.confirmedVersion ?? '暂无' }}</p>
          <p v-if="selected.sync.checkedAt" class="muted">最近核对：{{ selected.sync.checkedAt }}</p>
          <p v-if="selected.sync.lastError" class="muted">核对原因：{{ selected.sync.lastError }}</p>
          <p v-if="selected.sync.lastError === 'MANUALLY_PAUSED'">自动同步已暂停。</p>
          <div class="actions">
            <button v-if="selected.sync.state === 'PENDING'" class="secondary compact" :disabled="busy" @click="controlSync('pauses')">暂停自动同步</button>
            <button v-if="selected.sync.state !== 'CONFIRMED' && selected.sync.state !== 'REJECTED'" class="secondary compact" :disabled="busy" @click="controlSync('retries')">核对并恢复同步</button>
          </div>
        </div>
      </div>
    </article>
    <template v-else>
      <div class="list-controls"><label v-if="admin">状态筛选 <select v-model="filter" :disabled="busy" @change="load(1)"><option value="">全部</option><option value="ON_SALE">在售</option><option value="OFF_SALE">下架</option></select></label><button class="secondary compact" :disabled="busy" @click="load()">刷新列表</button></div>
      <p v-if="!busy && !listing.items.length" class="empty">{{ admin ? '暂无商品，点击创建商品开始维护。' : '暂无在售商品。' }}</p>
      <div class="product-grid"><article v-for="p in listing.items" :key="p.goodsId" class="product-tile">
        <img v-if="p.imageUrl && !broken[p.goodsId]" :src="p.imageUrl" :alt="p.goodsName" referrerpolicy="no-referrer" @error="broken[p.goodsId]=true"><div v-else class="image-placeholder">商品图片暂无</div>
        <h2>{{ p.goodsName }}</h2><p v-if="p.availability">{{ p.availability==='IN_STOCK'?'有货':'暂时缺货' }}</p><p class="product-price">¥ {{ p.originalPrice }}</p><p v-if="admin" class="muted">{{ p.saleStatus==='ON_SALE'?'在售':'下架' }} · 版本 {{ p.productVersion }}</p><p v-if="!p.syncReady" class="muted">资料更新中，暂不可试算</p><button @click="detail(p)" :disabled="busy">查看详情</button>
      </article></div>
      <div class="pagination"><button class="secondary compact" :disabled="busy || listing.page<=1" @click="load(listing.page-1)">上一页</button><span>第 {{ listing.page }} 页 · 共 {{ listing.total }} 件</span><button class="secondary compact" :disabled="busy || listing.page*listing.size>=listing.total" @click="load(listing.page+1)">下一页</button></div>
    </template>
    <aside v-if="admin" class="sync-quarantine" aria-label="同步隔离记录">
      <h2>同步隔离记录</h2><p class="muted">查看异常记录以便核对；配置修复后的恢复由维护人员处理。</p>
      <button class="secondary compact" :disabled="busy" @click="readQuarantine()">查询隔离记录</button>
      <template v-if="quarantine">
        <p>共 {{ quarantine.total }} 条 · 第 {{ quarantine.page }} 页</p>
        <p v-if="!quarantine.items.length">暂无隔离记录。</p>
        <table v-else><thead><tr><th>记录</th><th>原因</th><th>保存时间</th><th>状态</th></tr></thead><tbody><tr v-for="q in quarantine.items" :key="q.quarantineId"><td>{{ q.quarantineId }}</td><td>{{ q.reason }}</td><td>{{ q.storedAt }}</td><td>{{ q.state === 'REPLAYED' ? '已恢复' : '待核对' }}</td></tr></tbody></table>
        <div class="actions"><button class="secondary compact" :disabled="busy || quarantine.page <= 1" @click="readQuarantine(quarantine.page-1)">上一页记录</button><button class="secondary compact" :disabled="busy || quarantine.page*quarantine.size >= quarantine.total" @click="readQuarantine(quarantine.page+1)">下一页记录</button></div>
      </template>
    </aside>
  </section>
</template>
