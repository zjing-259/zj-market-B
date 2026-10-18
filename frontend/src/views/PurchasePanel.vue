<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import type { Product, Trial } from '../types/product'
import type { Confirmation, Order, PendingPurchase } from '../types/order'
import { ApiError } from '../errors/ApiError'
import { user, request } from '../services/auth'
import { confirm, submit, recover, retry, pending, orderError } from '../services/orders'

const props = defineProps<{ product: Product; trial: Trial | null; teamId?: string; joinable?: boolean }>()
const emit = defineEmits<{ activity: [active: boolean]; refreshTrial: [] }>()
const confirmation = ref<Confirmation | null>(null)
const order = ref<Order | null>(null)
const unresolved = ref<PendingPurchase | null>(null)
const busy = ref(false)
const error = ref('')
const latestPrice = ref('')
const needsRefresh = ref(false)
const autoStopped = ref(false)
let sequence = 0
let timer: ReturnType<typeof setTimeout> | undefined
let deadline = 0

const canBuy = computed(() => !!user.value && props.product.availability === 'IN_STOCK' &&
  props.product.saleStatus === 'ON_SALE' && props.product.syncReady &&
  props.trial?.state === 'AVAILABLE' && !!props.trial.offer &&
  (!props.teamId || !!props.joinable) && !needsRefresh.value)

function sameOffer(a: NonNullable<Trial['offer']>, b: NonNullable<Trial['offer']>): boolean {
  return a.activityId === b.activityId && a.goodsId === b.goodsId &&
    a.productVersion === b.productVersion && a.payPrice === b.payPrice &&
    a.originalPrice === b.originalPrice && a.deductionPrice === b.deductionPrice &&
    a.targetCount === b.targetCount && a.currency === b.currency
}
function current(seq: number, owner: string): boolean {
  return seq === sequence && user.value?.userId === owner
}
function stop(): void { if (timer) clearTimeout(timer); timer = undefined }
function shouldPoll(): boolean {
  return !!unresolved.value || !!order.value && (order.value.status === 'PROCESSING' ||
    order.value.status === 'WAITING_PAYMENT' && !order.value.paymentEnabled)
}
function schedule(): void {
  stop()
  if (!shouldPoll() || document.hidden) return
  if (Date.now() >= deadline) { autoStopped.value = true; return }
  timer = setTimeout(() => void lookup(), 3000)
}
async function lookup(): Promise<void> {
  const owner = user.value?.userId
  if (!owner || busy.value || !shouldPoll()) return
  const seq = sequence
  busy.value = true
  try {
    const result = unresolved.value
      ? await recover(unresolved.value)
      : await request<Order>(`/orders/${encodeURIComponent(order.value!.orderId)}`, owner)
    if (!current(seq, owner)) return
    order.value = result
    unresolved.value = null
    error.value = ''
  } catch (cause) {
    if (current(seq, owner)) error.value = orderError(cause)
  } finally {
    if (current(seq, owner)) { busy.value = false; schedule() }
  }
}
async function reset(): Promise<void> {
  stop()
  const seq = ++sequence
  confirmation.value = null
  order.value = null
  error.value = ''
  latestPrice.value = ''
  needsRefresh.value = false
  autoStopped.value = false
  busy.value = false
  unresolved.value = pending(props.product.goodsId)
  deadline = Date.now() + 300000
  const owner = user.value?.userId
  if (!owner) return
  if (unresolved.value) { void lookup(); return }
  try {
    const existing = await request<Order | null>(`/products/${encodeURIComponent(props.product.goodsId)}/active-order`, owner)
    if (current(seq, owner)) { order.value = existing; schedule() }
  } catch (cause) {
    if (current(seq, owner)) error.value = orderError(cause)
  }
}
async function prepare(): Promise<void> {
  const owner = user.value?.userId
  const expected = props.trial?.offer
  if (!owner || !expected || !canBuy.value || busy.value || order.value || unresolved.value) return
  const seq = sequence
  const selectedTeam = props.teamId
  busy.value = true
  error.value = ''
  try {
    const existing = await request<Order | null>(`/products/${encodeURIComponent(props.product.goodsId)}/active-order`, owner)
    if (!current(seq, owner)) return
    if (existing) { order.value = existing; schedule(); return }
    const next = await confirm(props.product.goodsId, expected, owner, selectedTeam)
    if (!current(seq, owner) || selectedTeam !== props.teamId ||
      !props.trial?.offer || !sameOffer(props.trial.offer, expected)) return
    if (next.mode !== (selectedTeam ? 'JOIN' : 'OPEN') || next.teamId !== (selectedTeam ?? null) ||
      !sameOffer(next.offer, expected)) {
      needsRefresh.value = true
      error.value = '购买条件已经变化，请重新读取优惠后再次确认。'
      return
    }
    confirmation.value = next
  } catch (cause) {
    if (!current(seq, owner)) return
    error.value = orderError(cause)
    if (cause instanceof ApiError && cause.code === 'OFFER_CHANGED') {
      needsRefresh.value = true
      const value = (cause.data as { latestOffer?: { payPrice?: unknown } } | null)?.latestOffer?.payPrice
      if (typeof value === 'string' && /^(?:0\.(?:0[1-9]|[1-9][0-9])|[1-9][0-9]{0,5}\.[0-9]{2})$/.test(value)) latestPrice.value = value
    }
  } finally { if (current(seq, owner)) busy.value = false }
}
async function purchase(original = false): Promise<void> {
  const owner = user.value?.userId
  if (!owner || busy.value) return
  if (!original && (!confirmation.value || Date.now() >= Date.parse(confirmation.value.expiresAt))) {
    confirmation.value = null
    error.value = '报价确认已过期，请重新读取优惠并再次确认。'
    return
  }
  const seq = sequence
  busy.value = true
  error.value = ''
  try {
    const result = original && unresolved.value
      ? await retry(unresolved.value)
      : await submit(props.product.goodsId, confirmation.value!.confirmationId, owner)
    if (!current(seq, owner)) return
    order.value = result
    unresolved.value = null
    confirmation.value = null
    deadline = Date.now() + 300000
    autoStopped.value = false
  } catch (cause) {
    if (!current(seq, owner)) return
    error.value = orderError(cause)
    unresolved.value = pending(props.product.goodsId)
    if (!unresolved.value) confirmation.value = null
    if (cause instanceof ApiError && ['OFFER_CHANGED', 'CONFIRMATION_EXPIRED', 'TEAM_OFFER_MISMATCH'].includes(cause.code)) needsRefresh.value = true
    deadline = Date.now() + 300000
  } finally {
    if (current(seq, owner)) { busy.value = false; schedule() }
  }
}
function visibility(): void { if (document.hidden) stop(); else if (shouldPoll()) void lookup() }
function refresh(): void { confirmation.value = null; emit('refreshTrial') }
function manualCheck(): void { deadline = Date.now() + 300000; autoStopped.value = false; void lookup() }
watch(() => [user.value?.userId, props.product.goodsId, props.product.productVersion, props.teamId, props.joinable], () => void reset())
watch(() => props.trial, () => { confirmation.value = null; needsRefresh.value = false; latestPrice.value = '' })
watch([confirmation, unresolved, busy], () => emit('activity', !!confirmation.value || !!unresolved.value || busy.value), { immediate: true })
onMounted(() => { document.addEventListener('visibilitychange', visibility); void reset() })
onUnmounted(() => { sequence++; stop(); document.removeEventListener('visibilitychange', visibility) })
</script>

<template>
  <section class="purchase-panel" aria-label="购买操作">
    <h3>{{ teamId ? '加入这个团队' : '单独开团' }}</h3>
    <p v-if="!user">登录后可查看适用优惠并购买。</p>
    <template v-else>
      <p v-if="error" class="message error" role="alert">{{ error }}</p>
      <p v-if="latestPrice">当前可能的实付价为 ¥ {{ latestPrice }}；旧确认不会自动采用新报价。</p>
      <button v-if="needsRefresh" class="secondary" :disabled="busy" @click="refresh">重新读取优惠</button>

      <div v-if="order" class="purchase-progress" role="status">
        <strong>{{ order.paymentEnabled ? '可以继续模拟支付' : order.status === 'PROCESSING' ? '订单正在确认' : '请核对原订单' }}</strong>
        <p>{{ order.paymentEnabled ? '后端已开放付款入口，请核对订单后继续。' : '正在查询原订单进度，不会再次创建购买。' }}</p>
        <a v-if="order.paymentEnabled" class="purchase-primary-link" :href="`/orders/${encodeURIComponent(order.orderId)}/payment`">查看订单并去支付</a>
        <a v-else :href="`/orders/${encodeURIComponent(order.orderId)}`">查看原订单</a>
        <button v-if="shouldPoll()" class="secondary" :disabled="busy" @click="manualCheck">刷新订单进度</button>
        <p v-if="autoStopped" class="muted">自动查询已暂停，可手动刷新。</p>
        <details><summary>订单信息</summary><p>订单编号：{{ order.orderId }}</p></details>
      </div>
      <div v-else-if="unresolved" class="purchase-progress" role="status">
        <strong>购买结果待核对</strong>
        <p>原请求可能已受理，请先查询原购买；重试也只使用原编号。</p>
        <button :disabled="busy" @click="manualCheck">查询原购买</button>
        <button class="secondary" :disabled="busy" @click="purchase(true)">用原编号重试</button>
        <p v-if="autoStopped" class="muted">自动查询已暂停，可手动查询。</p>
        <details><summary>支持信息</summary><p>原购买编号：{{ unresolved.purchaseIntentId }}</p></details>
      </div>
      <div v-else-if="confirmation" class="purchase-confirmation">
        <h4>确认本次购买</h4>
        <p><strong>{{ product.goodsName }}</strong> · 数量 1</p>
        <p>{{ teamId ? '加入指定团队' : '单独开团' }} · {{ confirmation.offer.targetCount }} 人成团</p>
        <p class="purchase-amount">本次实付 ¥ {{ confirmation.offer.payPrice }}</p>
        <p class="muted">请在 {{ new Date(confirmation.expiresAt).toLocaleTimeString('zh-CN') }} 前确认；提交时仍由服务端核验价格、库存和名额。</p>
        <div class="actions"><button :disabled="busy" @click="purchase()">确认下单并去支付</button><button class="secondary" :disabled="busy" @click="confirmation=null">返回商品</button></div>
        <details><summary>购买信息</summary><p>商品原价 ¥ {{ confirmation.offer.originalPrice }} · 优惠 ¥ {{ confirmation.offer.deductionPrice }}</p><p v-if="teamId">指定团队：{{ teamId }}</p></details>
      </div>
      <template v-else>
        <p v-if="product.availability === 'OUT_OF_STOCK'">当前缺货，暂不能购买。</p>
        <p v-else-if="!product.syncReady">商品资料正在更新，请稍后再看。</p>
        <p v-else-if="teamId && !joinable">该团队已满或暂不可加入，不会改为新开团。</p>
        <p v-else-if="trial?.state === 'NO_PUBLIC_OFFER'">暂无可参与的优惠活动。</p>
        <p v-else-if="trial?.state === 'INELIGIBLE'">当前账号暂不符合活动条件。</p>
        <p v-else-if="!trial">正在核对当前优惠；如等待较久，可重新读取。</p>
        <button v-if="canBuy" :disabled="busy" @click="prepare">{{ teamId ? '加入此团队' : '单独开团' }}</button>
      </template>
    </template>
  </section>
</template>
