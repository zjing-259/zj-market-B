<script setup lang="ts">
import type { Page } from '../navigation'
defineProps<{ page: Page; signedIn: boolean; operator: boolean }>()
defineEmits<{ navigate: [path: string] }>()
</script>

<template>
  <div class="shell store-shell">
    <a class="skip-link" href="#page-content">跳到主要内容</a>
    <header class="site-header">
      <a class="brand" href="/" @click.prevent="$emit('navigate', '/')">正经商城</a>
      <nav class="site-nav" aria-label="商城导航">
        <a href="/products" :aria-current="page === 'products' ? 'page' : undefined" @click.prevent="$emit('navigate', '/products')">商城首页</a>
        <a href="/orders" :aria-current="page === 'orders' || page === 'payment' ? 'page' : undefined" @click.prevent="$emit('navigate', '/orders')">我的订单</a>
        <a v-if="operator" href="/admin/products" @click.prevent="$emit('navigate', '/admin/products')">运营工作台</a>
        <a :href="signedIn ? '/account' : '/login'" :aria-current="['account','login','register'].includes(page) ? 'page' : undefined" @click.prevent="$emit('navigate', signedIn ? '/account' : '/login')">{{ signedIn ? '账号中心' : '登录／注册' }}</a>
      </nav>
    </header>
    <div id="page-content" class="store-content" tabindex="-1"><slot /></div>
    <footer>正经商城 · 认真挑选，安心下单</footer>
  </div>
</template>
