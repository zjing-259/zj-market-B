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
    <a class="skip-link" href="#page-content">跳到主要内容</a>
    <header class="site-header">
      <a class="brand" href="/" @click.prevent="$emit('navigate', '/')">正经商城</a>
      <nav class="site-nav" aria-label="运营快捷导航"><a href="/products" @click.prevent="$emit('navigate', '/products')">返回商城</a><a href="/account" @click.prevent="$emit('navigate', '/account')">账号中心</a></nav>
    </header>
    <div class="operator-workspace">
      <aside class="operator-sidebar"><p class="eyebrow">运营工作台</p><p class="muted">商品与库存维护、异常核对</p><nav aria-label="运营导航">
        <a v-for="link in links" :key="link.path" :href="link.path" :aria-current="page === link.page ? 'page' : undefined" @click.prevent="$emit('navigate', link.path)">{{ link.label }}</a>
      </nav><p class="operator-help">操作前核对当前记录；结果未明时先查原操作。</p></aside>
      <div id="page-content" class="operator-content" tabindex="-1"><slot /></div>
    </div>
    <footer>正经商城 · 运营工作台</footer>
  </div>
</template>
