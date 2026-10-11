<script setup lang="ts">
import type {RefundSummary} from '../types/refund'
import {fundsLabel,syncLabel,releaseLabel} from '../services/refunds'
defineProps<{refund:RefundSummary}>()
</script>
<template><section aria-label="退款进度" class="refund-progress"><h3>退款进度</h3><p>{{fundsLabel(refund.fundsStatus)}} · ¥ {{refund.refundAmount}}</p><p>{{syncLabel(refund.syncStatus)}} · {{releaseLabel(refund.releaseStatus)}}</p><p v-if="refund.refundedAt">退款时间：{{new Date(refund.refundedAt).toLocaleString()}}</p><small>原支付记录保留。退款、同步确认和库存收尾分别显示进度。</small></section></template>
