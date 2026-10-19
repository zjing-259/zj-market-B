<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { user, request } from '../services/auth'
import { pendingAction, startAction, retryAction, type Action } from '../services/orderLifecycle'
import RefundProgress from '../components/RefundProgress.vue'
import { orderError } from '../services/orders'
import type { Order, OrderPage } from '../types/order'

const id = location.pathname.split('/')[2]
const orders = ref<OrderPage>({ items: [], page: 1, size: 20, total: 0 })
const selected = ref<Order | null>(null), error = ref(''), busy = ref(false), expired = ref(false)
const confirmCancel = ref(false), reason = ref('用户不再需要此商品')
const actionPending = ref<Action | null>(id ? pendingAction(id, 'cancel') : null)
let sequence = 0, timer: ReturnType<typeof setTimeout> | undefined, deadline = Date.now() + 300000

function status(order: Order): string {
  if (order.refundSummary?.fundsStatus === 'SUCCEEDED')
    return ['RELEASED', 'ALREADY_RELEASED'].includes(order.refundSummary.releaseStatus) && order.status === 'CLOSED'
      ? '已全额退款，订单已关闭' : '退款已成功，订单正在收尾'
  const labels: Record<Order['status'], string> = {
    PROCESSING: '正在确认订单', WAITING_PAYMENT: '待付款', PAYMENT_PROCESSING: '正在确认付款结果',
    PAID_WAITING_A: '已付款，正在确认参团', PAID_WAITING_TEAM: '拼团中',
    WAITING_REFUND: '拼团未成功，退款处理中',
    GROUP_COMPLETED: order.fulfillmentSummary ? '成团成功，待履约' : '成团结果核对中',
    CLOSING: '正在关闭订单', CLOSED: '订单已关闭'
  }
  return labels[order.status]
}
function nextAction(order: Order): { path: string; label: string } | null {
  if (order.paymentEnabled) return { path: `/orders/${encodeURIComponent(order.orderId)}/payment`, label: '去模拟支付' }
  if (order.status === 'PAYMENT_PROCESSING' || order.paymentSummary)
    return { path: `/orders/${encodeURIComponent(order.orderId)}/payment`, label: '查看付款结果' }
  if (order.teamId && ['PAID_WAITING_A', 'PAID_WAITING_TEAM', 'GROUP_COMPLETED'].includes(order.status))
    return { path: `/teams/${encodeURIComponent(order.teamId)}`, label: '查看拼团与邀请好友' }
  return null
}
const selectedAction = computed(() => selected.value ? nextAction(selected.value) : null)
async function cancel(original = false) {
  const owner = user.value?.userId
  if (!owner || !selected.value || busy.value || !original && !selected.value.canCancel) return
  const seq = sequence
  busy.value = true; error.value = ''
  try {
    const result = original && actionPending.value
      ? await retryAction<Order>(actionPending.value)
      : await startAction<Order>(selected.value.orderId, 'cancel', reason.value.trim() || '用户申请关闭订单')
    if (seq === sequence && user.value?.userId === owner) {
      selected.value = result; actionPending.value = null; confirmCancel.value = false
      deadline = Date.now() + 300000
    }
  } catch (cause) { if (seq === sequence) error.value = orderError(cause) }
  finally {
    if (seq === sequence) { actionPending.value = id ? pendingAction(id, 'cancel') : null; busy.value = false; schedule() }
  }
}
function stop() { if (timer) clearTimeout(timer); timer = undefined }
function schedule() {
  stop()
  if (!id || document.hidden || Date.now() >= deadline || !selected.value) { expired.value = Date.now() >= deadline; return }
  if (['PROCESSING', 'CLOSING', 'PAYMENT_PROCESSING', 'PAID_WAITING_A', 'PAID_WAITING_TEAM', 'WAITING_REFUND'].includes(selected.value.status) ||
    selected.value.refundSummary && (!['RELEASED', 'ALREADY_RELEASED'].includes(selected.value.refundSummary.releaseStatus) ||
      !['ACCEPTED', 'REVIEW_REQUIRED'].includes(selected.value.refundSummary.syncStatus)))
    timer = setTimeout(() => void load(), 3000)
}
async function load(page = orders.value.page) {
  const owner = user.value?.userId
  if (!owner || busy.value) return
  const seq = sequence
  busy.value = true; error.value = ''
  try {
    if (id) {
      const next = await request<Order>(`/orders/${encodeURIComponent(id)}`, owner)
      if (seq === sequence && user.value?.userId === owner) selected.value = next
    } else {
      const next = await request<OrderPage>(`/orders?page=${page}&size=20`, owner)
      if (seq === sequence && user.value?.userId === owner) orders.value = next
    }
  } catch (cause) { if (seq === sequence) error.value = orderError(cause) }
  finally { if (seq === sequence) { busy.value = false; schedule() } }
}
function manualLoad(page = orders.value.page) { deadline = Date.now() + 300000; expired.value = false; void load(page) }
function visibility() { if (document.hidden) stop(); else if (Date.now() < deadline) void load() }
watch(() => user.value?.userId, () => {
  sequence++; stop(); actionPending.value = id ? pendingAction(id, 'cancel') : null
  selected.value = null; orders.value = { items: [], page: 1, size: 20, total: 0 }
  busy.value = false; confirmCancel.value = false; deadline = Date.now() + 300000; void load()
})
onMounted(() => { document.addEventListener('visibilitychange', visibility); void load() })
onUnmounted(() => { sequence++; stop(); document.removeEventListener('visibilitychange', visibility) })
</script>

<template>
  <section class="orders-page">
    <p class="eyebrow">正经商城 · 我的订单</p><h1>{{ selected ? '订单详情' : '我的订单' }}</h1>
    <p v-if="!user">请登录后查看本人订单。<a href="/login?returnTo=/orders">去登录</a></p>
    <template v-else>
      <p v-if="error" class="message error" role="alert">{{ error }}</p>
      <p v-if="expired" class="muted">自动查询已暂停，可手动刷新。</p>
      <button class="secondary" :disabled="busy" @click="manualLoad()">刷新订单</button>
      <template v-if="selected">
        <article class="order-detail">
          <div class="order-status" role="status"><strong>{{ status(selected) }}</strong>
            <p v-if="selected.status === 'PROCESSING'">正在确认购买，请等待原订单结果。</p>
            <p v-else-if="selected.status === 'CLOSING'">正在核对付款并确认关闭；当前不能视为已取消。</p>
            <p v-else-if="selected.status === 'PAID_WAITING_A'">付款已确认，正在核对参团结果。</p>
            <p v-else-if="selected.status === 'GROUP_COMPLETED' && selected.fulfillmentSummary">成团与库存确认已完成，等待后续履约。</p>
          </div>
          <div class="order-product"><img v-if="selected.product.imageUrl" :src="selected.product.imageUrl" alt="">
            <div><h2>{{ selected.product.name }}</h2><p>{{ selected.mode === 'JOIN' ? '加入指定团队' : '单独开团' }} · 数量 {{ selected.quantity }}</p>
              <p class="order-amount">实付 ¥ {{ selected.offer.payPrice }}</p></div></div>
          <RefundProgress v-if="selected.refundSummary" :refund="selected.refundSummary" />
          <p v-if="selected.reviewRequired && !selected.refundSummary" class="message error">此订单需要后台核对，请保留原订单，不要重复购买。</p>
          <p v-if="selected.teamId && selected.paymentDeadline" class="muted">付款期限：{{ new Date(selected.paymentDeadline).toLocaleString('zh-CN') }}</p>
          <div class="actions"><a v-if="selectedAction" class="purchase-primary-link" :href="selectedAction.path">{{ selectedAction.label }}</a>
            <a v-if="selected.teamId && selectedAction?.path !== `/teams/${encodeURIComponent(selected.teamId)}`" :href="`/teams/${encodeURIComponent(selected.teamId)}`">查看团队</a>
            <a href="/orders">返回订单列表</a></div>
          <div v-if="actionPending" class="order-cancel-state" role="status"><strong>关闭结果待核对</strong>
            <p>原请求可能已受理，请刷新订单；重试只使用原编号。</p>
            <button class="secondary" :disabled="busy" @click="cancel(true)">用原编号重试关闭</button></div>
          <div v-else-if="selected.canCancel" class="order-cancel-state">
            <button v-if="!confirmCancel" class="secondary" :disabled="busy" @click="confirmCancel=true">取消未付款订单</button>
            <form v-else @submit.prevent="cancel()"><h3>确认申请关闭订单？</h3>
              <p>提交后仍需核对付款与关闭结果，不能立即视为已取消。</p>
              <label for="cancelReason">原因</label><select id="cancelReason" v-model="reason" :disabled="busy">
                <option>用户不再需要此商品</option><option>购买信息需要调整</option><option>其他原因</option></select>
              <div class="actions"><button :disabled="busy">确认申请关闭</button><button type="button" class="secondary" :disabled="busy" @click="confirmCancel=false">返回订单</button></div>
            </form>
          </div>
          <details class="support-details"><summary>订单与支持信息</summary>
            <p>订单编号：{{ selected.orderId }} · 创建于 {{ new Date(selected.createdAt).toLocaleString('zh-CN') }}</p>
            <p>商品版本：{{ selected.product.productVersion }}</p><p v-if="selected.teamId">团队编号：{{ selected.teamId }}</p>
            <p v-if="selected.errorCode">当前核对代码：{{ selected.errorCode }}</p>
            <p v-if="actionPending">原关闭编号：{{ actionPending.body.operationId }}</p>
            <p v-if="selected.closedAt">关闭于 {{ new Date(selected.closedAt).toLocaleString('zh-CN') }}；依据 {{ selected.closeBasis }}</p>
          </details>
        </article>
      </template>
      <template v-else-if="!id">
        <p v-if="!orders.items.length && !busy && !error" class="empty">暂无订单，可从商城首页选择商品。</p>
        <div class="order-list"><article v-for="item in orders.items" :key="item.orderId" class="order-card">
          <img v-if="item.product.imageUrl" :src="item.product.imageUrl" alt="">
          <div><p class="eyebrow">{{ item.mode === 'JOIN' ? '加入团队' : '单独开团' }}</p><h2>{{ item.product.name }}</h2>
            <p>{{ status(item) }}</p><p class="order-amount">¥ {{ item.offer.payPrice }}</p>
            <a :href="`/orders/${encodeURIComponent(item.orderId)}`">查看订单与进度</a></div></article></div>
        <div class="pagination"><button class="secondary" :disabled="busy || orders.page <= 1" @click="manualLoad(orders.page-1)">上一页</button>
          <span>第 {{ orders.page }} 页</span><button class="secondary" :disabled="busy || orders.page*orders.size >= orders.total" @click="manualLoad(orders.page+1)">下一页</button></div>
      </template>
    </template>
  </section>
</template>
