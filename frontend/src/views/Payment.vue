<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { user, request, explain } from '../services/auth'
import { getPayment, pendingPayment, paymentOperation, retryPayment, createAttempt, chooseResult,
  paymentFlow, savePaymentFlow, clearPaymentFlow } from '../services/payments'
import type { PaymentFlow } from '../services/payments'
import type { OrderPayment, PendingPayment, PaymentOperation } from '../types/payment'
import type { Order } from '../types/order'

const orderId = location.pathname.split('/')[2] ?? ''
const view = ref<OrderPayment | null>(null), order = ref<Order | null>(null)
const pending = ref<PendingPayment | null>(null), flow = ref<PaymentFlow | null>(null)
const operation = ref<PaymentOperation | null>(null), busy = ref(false), error = ref(''), stopped = ref(false)
const active = computed(() => view.value?.payment?.attempts.find(a => a.attemptId === view.value?.payment?.activeAttemptId))
const paymentDone = computed(() => view.value?.payment?.fundsState === 'SUCCEEDED')
const now = ref(Date.now())
const remaining = computed(() => {
  const deadline = view.value?.payment?.paymentDeadline ?? order.value?.paymentDeadline
  if (!deadline) return null
  const seconds = Math.max(0, Math.ceil((Date.parse(deadline) - now.value) / 1000))
  return seconds ? `${Math.floor(seconds / 60)} 分 ${String(seconds % 60).padStart(2, '0')} 秒` : '已到期，付款资格以服务端为准'
})
const canChoose = computed(() => !pending.value && !flow.value && !view.value?.payment?.reviewRequired && !paymentDone.value &&
  (active.value?.canSelectResult || view.value?.canCreateAttempt))
const resultLabels = { SUCCEEDED: '模拟支付成功', FAILED: '模拟本次支付失败' }
const attemptLabels: Record<string, string> = { CREATING: '正在创建支付记录', OPEN: '等待模拟支付', UNKNOWN: '结果待核对',
  FAILED: '本次模拟支付失败', SUCCEEDED: '渠道已确认成功', CLOSED_UNPAID: '未付款且已关闭' }
let generation = 0, timer: ReturnType<typeof setTimeout> | undefined, clock: ReturnType<typeof setInterval> | undefined, until = Date.now() + 300000
function stop() { if (timer) clearTimeout(timer); timer = undefined }
function schedule() {
  stop()
  if (!user.value || document.hidden || Date.now() >= until) { stopped.value = Date.now() >= until; return }
  if (pending.value || flow.value || ['CREATING', 'UNKNOWN'].includes(active.value?.state ?? '') ||
    view.value?.payment?.fundsState === 'UNKNOWN' ||
    paymentDone.value && view.value?.payment?.aAcceptance === 'PENDING') timer = setTimeout(() => void load(), 2500)
}
async function read(owner: string, seq: number) {
  const original = pendingPayment(owner, orderId)
  if (seq === generation && user.value?.userId === owner) {
    pending.value = original
    flow.value = paymentFlow(owner, orderId)
  }
  let nextOperation: PaymentOperation | null = null
  if (original) nextOperation = await paymentOperation(original)
  const [nextPayment, nextOrder] = await Promise.all([
    getPayment(owner, orderId), request<Order>(`/orders/${encodeURIComponent(orderId)}`, owner)
  ])
  if (seq !== generation || user.value?.userId !== owner) return
  operation.value = nextOperation
  pending.value = pendingPayment(owner, orderId)
  flow.value = paymentFlow(owner, orderId)
  view.value = nextPayment
  order.value = nextOrder
  const currentAttempt = nextPayment.payment?.attempts.find(a => a.attemptId === nextPayment.payment?.activeAttemptId)
  if (flow.value && (nextOperation?.progress === 'REJECTED' ||
    flow.value.attemptId === currentAttempt?.attemptId && ['FAILED', 'SUCCEEDED', 'CLOSED_UNPAID'].includes(currentAttempt.state) ||
    nextPayment.payment?.fundsState === 'SUCCEEDED' || nextPayment.payment?.reviewRequired)) {
    clearPaymentFlow(flow.value)
    flow.value = null
  }
}
async function load() {
  const owner = user.value?.userId
  if (!owner || busy.value) return
  const seq = generation
  busy.value = true; error.value = ''
  try { await read(owner, seq) } catch (cause) { if (seq === generation) error.value = explain(cause) }
  finally { if (seq === generation) { busy.value = false; schedule() } }
}
const wait = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))
async function advance(owner: string, seq: number) {
  await read(owner, seq)
  if (seq !== generation || pending.value || !flow.value || !view.value || view.value.payment?.reviewRequired || paymentDone.value || flow.value.phase === 'RESULT_SENT') return
  let intent = flow.value
  let current = active.value
  if (intent.attemptId && current?.attemptId !== intent.attemptId) return
  if (!current?.canSelectResult) {
    if (intent.attemptId || !view.value.canCreateAttempt) return
    await createAttempt(owner, orderId, current?.state === 'FAILED' ? current.attemptId : null)
    for (let i = 0; i < 8; i++) {
      await wait(350); await read(owner, seq)
      if (seq !== generation || !flow.value || operation.value?.progress === 'REJECTED') return
      if (pending.value) continue
      if (active.value?.canSelectResult) break
    }
    current = active.value
    if (!current?.canSelectResult) return
  }
  intent = { ...intent, attemptId: current.attemptId, phase: 'RESULT_SENT' }
  savePaymentFlow(intent); flow.value = intent
  await chooseResult(owner, orderId, view.value.payment!.paymentId, current.attemptId, intent.result)
  await read(owner, seq)
}
async function choose(result: PaymentFlow['result'] | null = null) {
  const owner = user.value?.userId
  if (!owner || busy.value || !navigator.locks) return
  const seq = generation
  const expectedAttempt = active.value?.attemptId ?? null
  const expectedState = active.value?.state ?? null
  busy.value = true; error.value = ''
  try {
    await navigator.locks.request(`b-payment-flow:${owner}:${orderId}`, async () => {
      if (seq !== generation || user.value?.userId !== owner) return
      const existing = paymentFlow(owner, orderId)
      if (!existing) {
        if (!result || pendingPayment(owner, orderId)) return
        await read(owner, seq)
        if (seq !== generation || user.value?.userId !== owner) return
        if ((active.value?.attemptId ?? null) !== expectedAttempt || (active.value?.state ?? null) !== expectedState || !canChoose.value) {
          error.value = '付款记录已经变化，请核对后重新选择。'
          return
        }
        savePaymentFlow({ owner, orderId, result, attemptId: null, phase: 'PREPARE' })
      }
      await advance(owner, seq)
    })
  } catch (cause) { if (seq === generation) error.value = explain(cause) }
  finally { if (seq === generation) { busy.value = false; until = Date.now() + 300000; schedule() } }
}
async function retryOriginal() {
  const owner = user.value?.userId
  if (!owner || busy.value || !pending.value) return
  const seq = generation
  busy.value = true; error.value = ''
  try { await retryPayment(pending.value); await read(owner, seq) }
  catch (cause) { if (seq === generation) error.value = explain(cause) }
  finally { if (seq === generation) { busy.value = false; schedule() } }
}
function manualRead() { until = Date.now() + 300000; stopped.value = false; void load() }
function visible() { if (document.hidden) stop(); else if (Date.now() < until) void load() }
watch(() => user.value?.userId, () => {
  generation++; stop(); view.value = null; order.value = null; pending.value = null; flow.value = null
  operation.value = null; error.value = ''; busy.value = false; until = Date.now() + 300000; void load()
})
onMounted(() => { document.addEventListener('visibilitychange', visible); clock = setInterval(() => { now.value = Date.now() }, 1000); void load() })
onUnmounted(() => { generation++; stop(); if (clock) clearInterval(clock); document.removeEventListener('visibilitychange', visible) })
</script>

<template>
  <section class="payment-page">
    <p class="eyebrow">正经商城 · 模拟收银台</p><h1>确认本次付款</h1>
    <p class="muted">演示支付，不产生真实扣款。</p>
    <p v-if="!user">请登录后查看本人收银台。<a :href="`/login?returnTo=${encodeURIComponent(`/orders/${orderId}/payment`)}`">去登录</a></p>
    <template v-else>
      <p v-if="error" class="message error" role="alert">{{ error }}</p>
      <div v-if="order && view" class="payment-card">
        <p class="eyebrow">{{ order.product.name }}</p>
        <p class="payment-amount">¥ {{ view.payment?.amount ?? order.offer.payPrice }}</p>
        <p>{{ order.mode === 'JOIN' ? '加入团队' : '单独开团' }} · 数量 {{ order.quantity }}</p>
        <p v-if="view.payment?.paymentDeadline">请在 {{ new Date(view.payment.paymentDeadline).toLocaleString('zh-CN') }} 前完成模拟支付。</p>
        <p v-if="remaining && !paymentDone">付款倒计时：{{ remaining }}</p>
        <p v-if="active" role="status">{{ paymentDone && active.state === 'SUCCEEDED' ? '模拟支付已成功' : attemptLabels[active.state] }}</p>
        <p v-if="view.payment?.fundsState === 'UNKNOWN'" role="status">付款结果正在核对，请等待原操作结果。</p>
        <p v-if="paymentDone" role="status">{{ view.payment?.aAcceptance === 'REJECTED' ? '付款已确认，参团未被接受，退款将继续处理。' : view.payment?.aAcceptance === 'ACCEPTED' ? '付款已确认，正在等待成团。' : '付款已确认，正在核对参团结果。' }}</p>
        <p v-if="view.payment?.reviewRequired" class="message error">付款需要后台核对，暂不能重新操作。</p>
        <div v-if="canChoose" class="payment-actions">
          <button :disabled="busy" @click="choose('SUCCEEDED')">{{ active?.state === 'FAILED' ? '再次模拟支付成功' : '模拟支付成功' }}</button>
          <button class="secondary" :disabled="busy" @click="choose('FAILED')">模拟本次支付失败</button>
        </div>
        <p v-if="active?.state === 'FAILED' && !pending && !flow">本次失败未扣款；付款期限内可明确选择再次模拟支付。</p>
        <p v-if="!canChoose && !paymentDone && !pending && !flow && !view.payment?.reviewRequired">当前订单暂不能开始新的付款，请核对原记录。</p>
      </div>
      <div v-if="flow || pending" class="payment-progress" role="status">
        <strong>正在确认本次模拟支付</strong>
        <p v-if="flow">已保留“{{ resultLabels[flow.result] }}”的选择。刷新页面只查询原记录，不自动提交新的付款。</p>
        <p v-if="pending">原操作结果尚未确定；查询未找到记录也不能证明写入失败。</p>
        <div class="actions"><button class="secondary" :disabled="busy" @click="manualRead">查询原操作</button>
          <button v-if="pending" class="secondary" :disabled="busy" @click="retryOriginal">用原编号重试</button>
          <button v-else-if="flow?.phase === 'PREPARE'" :disabled="busy" @click="choose()">继续本次模拟支付</button></div>
      </div>
      <p v-if="stopped">自动查询已暂停，可手动查询。</p>
      <button class="secondary" :disabled="busy" @click="manualRead">刷新付款状态</button>
      <div v-if="order && view" class="payment-links"><a v-if="order.teamId" :href="`/teams/${encodeURIComponent(order.teamId)}`">查看拼团与邀请好友</a><a :href="`/orders/${encodeURIComponent(orderId)}`">查看原订单</a></div>
      <details class="support-details"><summary>支付与订单信息</summary><p>订单编号：{{ orderId }}</p><p v-if="view?.payment">支付编号：{{ view.payment.paymentId }}</p>
        <p v-if="pending">原操作编号：{{ pending.body.operationId }} · {{ operation?.progress ?? '待核对' }}</p>
        <p v-for="attempt in view?.payment?.attempts ?? []" :key="attempt.attemptId">第 {{ attempt.attemptNo }} 次：{{ attemptLabels[attempt.state] }} · {{ attempt.attemptId }}</p></details>
    </template>
  </section>
</template>
