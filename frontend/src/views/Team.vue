<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { user, request, publicGet, write, explain } from '../services/auth'
import type { Team } from '../types/order'
import type { Product, Trial } from '../types/product'
import PurchasePanel from './PurchasePanel.vue'

const team = ref<Team | null>(null)
const product = ref<Product | null>(null)
const trial = ref<Trial | null>(null)
const error = ref('')
const shareStatus = ref('')
const busy = ref(false)
let id = ''
try { id = decodeURIComponent(location.pathname.split('/')[2] ?? '') } catch { id = '' }
let sequence = 0
const shareUrl = computed(() => team.value ? new URL(`/teams/${encodeURIComponent(team.value.teamId)}`, location.origin).href : '')

async function load(): Promise<void> {
  const owner = user.value?.userId
  if (!owner || busy.value) return
  if (!id) { error.value = '团队链接无效，请重新选择团队。'; return }
  const seq = ++sequence
  busy.value = true
  error.value = ''
  shareStatus.value = ''
  trial.value = null
  team.value = null
  product.value = null
  try {
    const current = await request<Team>(`/teams/${encodeURIComponent(id)}`, owner)
    if (seq !== sequence || user.value?.userId !== owner) return
    team.value = current
    const goods = await publicGet<Product>(`/products/${encodeURIComponent(current.goodsId)}`)
    if (seq !== sequence || user.value?.userId !== owner) return
    product.value = goods
    if (goods.syncReady) {
      const quote = await write<Trial>(`/products/${encodeURIComponent(current.goodsId)}/trial`, 'POST', {}, owner)
      if (seq !== sequence || user.value?.userId !== owner) return
      if (quote.offer && (quote.offer.activityId !== current.activityId || quote.offer.targetCount !== current.targetCount)) {
        error.value = '活动或成团条件已变化，请重新核对团队；不会自动改成开团。'
      } else trial.value = quote
    }
  } catch (cause) { if (seq === sequence) error.value = explain(cause) }
  finally { if (seq === sequence) busy.value = false }
}
async function copyShare(): Promise<void> {
  if (!shareUrl.value) return
  try {
    if (!navigator.clipboard?.writeText) throw Error('Clipboard unavailable')
    await navigator.clipboard.writeText(shareUrl.value)
    shareStatus.value = '邀请链接已复制。'
  } catch { shareStatus.value = '无法自动复制，请选择下方地址手动复制。' }
}
watch(() => user.value?.userId, () => { sequence++; busy.value = false; team.value = null; product.value = null; trial.value = null; shareStatus.value = ''; void load() })
onMounted(() => void load())
onUnmounted(() => { sequence++ })
</script>

<template>
  <section class="team-page">
    <h1>拼团详情</h1>
    <p v-if="!user">请登录后查看团队详情。<a :href="`/login?returnTo=${encodeURIComponent(`/teams/${encodeURIComponent(id)}`)}`">去登录</a></p>
    <template v-else>
      <button class="secondary compact" :disabled="busy" @click="load">刷新团队与优惠</button>
      <p v-if="busy" role="status">正在核对团队…</p>
      <p v-if="error" role="alert" class="message error">{{ error }}</p>
      <article v-if="team" class="team-summary">
        <p class="eyebrow">拼团进度</p>
        <h2>还需 {{ Math.max(0, team.targetCount - team.paidCount) }} 人付款</h2>
        <p>已付款 {{ team.paidCount }} 人 · 已占 {{ team.reservedCount }} 位 · 可加入 {{ Math.max(0, team.targetCount - team.reservedCount) }} 位</p>
        <p>有效至 <time :datetime="team.validEndTime">{{ new Date(team.validEndTime).toLocaleString('zh-CN') }}</time></p>
        <p v-if="!team.joinable" role="status">当前团队暂不可加入，不会改为新开团。</p>
        <a v-if="team.myOrderId" :href="`/orders/${encodeURIComponent(team.myOrderId)}`">查看我的原订单</a>
        <div class="share-panel"><button class="secondary" @click="copyShare">复制邀请链接</button><p v-if="shareStatus" role="status">{{ shareStatus }}</p><label for="shareLink">邀请地址</label><input id="shareLink" readonly :value="shareUrl" @focus="($event.target as HTMLInputElement).select()"></div>
        <details class="support-details"><summary>团队信息</summary><p>团队编号：{{ team.teamId }}</p><p>当前状态：{{ team.status }}</p></details>
      </article>
      <article v-if="team && product" class="team-product">
        <h2>{{ product.goodsName }}</h2>
        <p>{{ product.availability === 'IN_STOCK' ? '有货' : '暂时缺货' }} · 原价 ¥ {{ product.originalPrice }}</p>
        <p v-if="trial?.state === 'AVAILABLE' && trial.offer" class="product-price">参团实付 ¥ {{ trial.offer.payPrice }}</p>
        <PurchasePanel :product="product" :trial="trial" :team-id="team.teamId" :joinable="team.joinable" @refresh-trial="load" />
      </article>
    </template>
  </section>
</template>
