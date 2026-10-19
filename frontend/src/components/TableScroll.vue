<script setup lang="ts">
defineProps<{ label: string }>()
</script>
<template><p class="table-hint muted">表格可左右滚动，键盘聚焦后可用方向键查看。</p><div class="table-scroll" role="region" :aria-label="label" tabindex="0"><slot /></div></template>
