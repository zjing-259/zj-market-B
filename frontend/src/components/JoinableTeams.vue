<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ApiError } from '../errors/ApiError'
import { user, explain } from '../services/auth'
import { joinableTeams } from '../services/team-discovery'
import type { Product } from '../types/product'
import type { JoinableTeam, TeamDiscovery } from '../types/team-discovery'

const props = defineProps<{ product: Product; purchaseBusy: boolean; canOpen: boolean }>()
const result = ref<TeamDiscovery | null>(null)
const cards = ref<JoinableTeam[]>([])
const error = ref('')
const busy = ref(false)
const expanded = ref(false)
const now = ref(0)
const retryAt = ref(0)
const autoStopped = ref(false)
const deadlines = new Map<string, number>()
let epoch = 0
let autoUntil = 0
let autoTimer: ReturnType<typeof setTimeout> | undefined
let clockTimer: ReturnType<typeof setInterval> | undefined
let expiryRefreshTriggered = false

const eligible = computed(() => !!user.value && user.value.roles.some(role => role === 'USER' || role === 'OPERATOR'))
const canRead = computed(() => eligible.value && props.product.saleStatus === 'ON_SALE')
const retrySeconds = computed(() => Math.max(0, Math.ceil((retryAt.value - now.value) / 1000)))

function clearAuto() { if (autoTimer) clearTimeout(autoTimer); autoTimer = undefined }
function remaining(team: JoinableTeam) { return Math.max(0, Math.ceil(((deadlines.get(team.teamId) ?? 0) - now.value) / 1000)) }
function countdown(team: JoinableTeam) {
  const seconds = remaining(team)
  if (!seconds) return '已到期'
  const hours = Math.floor(seconds / 3600)
  return `${hours.toString().padStart(2, '0')}:${Math.floor(seconds / 60 % 60).toString().padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}`
}
function schedule() {
  clearAuto()
  if (!canRead.value || busy.value || expanded.value || props.purchaseBusy || document.hidden || autoStopped.value || !result.value || result.value.state !== 'AVAILABLE') return
  if (performance.now() >= autoUntil) { autoStopped.value = true; return }
  autoTimer = setTimeout(() => {
    if (!busy.value && !document.hidden && !expanded.value && !props.purchaseBusy) void loadFirst()
  }, 15000)
}
function clearResult() {
  result.value = null; cards.value = []; deadlines.clear(); expanded.value = false
  expiryRefreshTriggered = false; clearAuto()
}
async function load(cursor?: string) {
  if (!canRead.value || busy.value || now.value < retryAt.value) return
  const owner = user.value!.userId, goods = props.product.goodsId, version = props.product.productVersion
  const seq = epoch
  busy.value = true; error.value = ''
  try {
    const page = await joinableTeams(goods, owner, cursor)
    if (seq !== epoch || user.value?.userId !== owner || props.product.goodsId !== goods || props.product.productVersion !== version) return
    if (page.goodsId !== goods || page.productVersion !== version) { clearResult(); error.value = '商品资料已变化，请刷新商品后重试。'; return }
    if (cursor && (page.state !== 'AVAILABLE' || result.value?.activityId !== page.activityId)) { clearResult(); error.value = '活动已变化，请重新加载待拼团队。'; return }
    const received = performance.now()
    const serverTime = page.serverTime ? Date.parse(page.serverTime) : NaN
    if (page.state === 'AVAILABLE' && !Number.isFinite(serverTime)) { clearResult(); error.value = '待拼团队时间暂不可确认，请手动重试。'; return }
    for (const item of page.items) deadlines.set(item.teamId, received + Math.max(0, Date.parse(item.validEndTime) - serverTime))
    cards.value = cursor ? [...cards.value, ...page.items.filter(item => !cards.value.some(old => old.teamId === item.teamId))] : page.items
    if (!cursor) { for (const id of deadlines.keys()) if (!page.items.some(item => item.teamId === id)) deadlines.delete(id); expiryRefreshTriggered = false }
    result.value = page
    now.value = received
  } catch (e) {
    if (seq !== epoch) return
    if (e instanceof ApiError && e.code === 'TEAM_DISCOVERY_CONTEXT_CHANGED' && cursor) { reset(); void loadFirst(); return }
    if (!cursor) clearResult()
    if (e instanceof ApiError && e.status === 429) { retryAt.value = performance.now() + Math.max(1, e.retryAfterSeconds ?? 60) * 1000; autoStopped.value = true }
    error.value = e instanceof ApiError && [502, 503].includes(e.status) ? `待拼团队暂时无法加载，请稍后手动重试。（请求编号 ${e.requestId}）` : explain(e)
  } finally { if (seq === epoch) { busy.value = false; schedule() } }
}
function loadFirst() { clearResult(); return load() }
function reset() {
  ++epoch; busy.value = false; error.value = ''; retryAt.value = 0; autoStopped.value = false
  clearResult(); autoUntil = performance.now() + 300000
}
function manualRefresh() { if (busy.value || retrySeconds.value) return; autoUntil = performance.now() + 300000; autoStopped.value = false; void loadFirst() }
function more() { if (!busy.value && result.value?.hasMore && result.value.nextCursor) void load(result.value.nextCursor) }
function tick() {
  now.value = performance.now()
  if (!expiryRefreshTriggered && cards.value.some(item => remaining(item) === 0)) {
    expiryRefreshTriggered = true
    if (!expanded.value && !busy.value && !props.purchaseBusy && !document.hidden && !autoStopped.value) void loadFirst()
  }
}
function visibility() {
  if (document.hidden) clearAuto()
  else if (canRead.value && !props.purchaseBusy && !busy.value) void loadFirst()
}
watch([() => props.product.goodsId, () => props.product.productVersion, () => props.product.saleStatus, () => props.product.syncReady, () => props.product.availability, () => user.value?.userId, () => eligible.value], () => {
  reset()
  if (canRead.value) void loadFirst()
}, { immediate: true })
watch(() => props.purchaseBusy, () => schedule())
onMounted(() => { document.addEventListener('visibilitychange', visibility); clockTimer = setInterval(tick, 1000) })
onUnmounted(() => { ++epoch; clearAuto(); if (clockTimer) clearInterval(clockTimer); document.removeEventListener('visibilitychange', visibility) })

const reasonText: Record<NonNullable<TeamDiscovery['reason']>, string> = {
  NO_OFFER: '暂无可参与的活动，当前不能开团。',
  INELIGIBLE: '你当前不符合该活动的参与条件。',
  PRODUCT_SYNC_PENDING: '商品资料正在同步，请稍后重试。',
  OUT_OF_STOCK: '商品暂时缺货，无法新建购买。'
}
</script>

<template>
  <section class="joinable-teams" aria-label="正在拼团">
    <h3>正在拼团</h3>
    <p v-if="!user">登录后查看可参与的拼团。<a :href="`/login?returnTo=${encodeURIComponent('/products/' + product.goodsId)}`">登录查看</a></p>
    <p v-else-if="!eligible" role="alert">当前账号无权查看待拼团队。</p>
    <template v-else>
      <p v-if="busy && !cards.length" role="status">正在加载待拼团队…</p>
      <p v-if="error" role="alert" class="message error">{{ error }}</p>
      <p v-if="retrySeconds" role="status">请 {{ retrySeconds }} 秒后重试。</p>
      <p v-if="result?.state === 'ACTIVE_PURCHASE'">你已有进行中的订单。<a v-if="result.activeOrderId" :href="`/orders/${encodeURIComponent(result.activeOrderId)}`">查看原订单</a></p>
      <p v-else-if="result?.state === 'UNAVAILABLE'">{{ result.reason ? reasonText[result.reason] : '待拼团队暂不可用。' }}</p>
      <p v-else-if="result?.state === 'AVAILABLE' && !cards.length">{{ canOpen ? '暂无可参与的拼团，可以自己开团。' : '暂无可参与的拼团，请先核对当前优惠。' }}</p>
      <ul v-if="cards.length && result?.state === 'AVAILABLE'" class="joinable-list">
        <li v-for="team in cards" :key="team.teamId" class="joinable-card">
          <p><strong>{{ team.targetCount }} 人团</strong> · 已支付 {{ team.paidCount }} 人 · 还需付款 {{ team.remainingPaidCount }} 人</p>
          <p>已占 {{ team.reservedCount }} 位 · 可加入 {{ team.availableSlots }} 位</p>
          <p>剩余时间 <time :datetime="team.validEndTime">{{ countdown(team) }}</time></p>
          <a v-if="remaining(team) > 0" class="joinable-action" :href="`/teams/${encodeURIComponent(team.teamId)}`">去参团</a>
          <span v-else class="muted">已到期，请刷新列表</span>
        </li>
      </ul>
      <div class="actions">
        <button v-if="result?.state === 'AVAILABLE' && result.hasMore" class="secondary compact" :disabled="busy" @click="expanded=true;more()">{{ busy ? '加载中…' : '查看更多' }}</button>
        <button class="secondary compact" :disabled="busy || retrySeconds > 0 || purchaseBusy" @click="manualRefresh">刷新待拼团队</button>
      </div>
      <p v-if="autoStopped && result?.state === 'AVAILABLE'" class="muted">自动刷新已暂停，可手动刷新。</p>
      <small class="muted">人数和倒计时仅供参考，参团时会重新核验团队及报价。</small>
    </template>
  </section>
</template>
