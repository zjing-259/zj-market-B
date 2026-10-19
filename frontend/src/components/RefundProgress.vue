<script setup lang="ts">
import type {RefundSummary} from '../types/refund'
import {fundsLabel,syncLabel,releaseLabel} from '../services/refunds'
defineProps<{refund:RefundSummary}>()
</script>
<template><section aria-label="退款进度" class="refund-progress"><h3>{{ refund.fundsStatus === 'SUCCEEDED' ? '已全额退款' : '退款进度' }}</h3>
  <p class="refund-amount">¥ {{ refund.refundAmount }} · {{ fundsLabel(refund.fundsStatus) }}</p>
  <p v-if="refund.fundsStatus === 'SUCCEEDED' && (refund.syncStatus !== 'ACCEPTED' || !['RELEASED','ALREADY_RELEASED'].includes(refund.releaseStatus))">退款已成功，订单正在收尾。</p>
  <p v-else-if="refund.fundsStatus === 'UNKNOWN'">退款结果正在核对，请勿重复支付或操作。</p>
  <p v-else-if="refund.fundsStatus === 'FAILED'">本次退款未成功，系统将依据原记录继续处理。</p>
  <details class="support-details"><summary>退款处理详情</summary><p>同步：{{ syncLabel(refund.syncStatus) }}</p><p>库存：{{ releaseLabel(refund.releaseStatus) }}</p>
    <p v-if="refund.refundedAt">资金退款时间：{{ new Date(refund.refundedAt).toLocaleString('zh-CN') }}</p></details>
</section></template>
