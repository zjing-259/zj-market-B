<script setup lang="ts">
import type { Page } from '../navigation'
defineProps<{ page: Page }>()
defineEmits<{ navigate: [path: string] }>()
const links = [
  { path: '/admin/products', label: '商品管理', page: 'admin' },
  { path: '/admin/inventory', label: '库存管理', page: 'inventory' },
  { path: '/admin/orders', label: '订单异常', page: 'exceptions' },
  { path: '/admin/refunds', label: '退款异常', page: 'refunds' },
  { path: '/admin/reconciliations', label: '团队核对', page: 'reconciliations' },
] as const
</script>

<template>
  <div class="shell operator-shell">
    <header class="site-header">
      <a class="brand" href="/" @click.prevent="$emit('navigate', '/')">正经商城</a>
      <nav class="site-nav" aria-label="运营导航">
        <a v-for="link in links" :key="link.path" :href="link.path" :aria-current="page === link.page ? 'page' : undefined" @click.prevent="$emit('navigate', link.path)">{{ link.label }}</a>
        <a href="/account" @click.prevent="$emit('navigate', '/account')">账号中心</a>
      </nav>
    </header>
    <slot />
    <footer>正经商城 · 运营工作台</footer>
  </div>
</template>
