<script setup lang="ts">
import type { User } from './types/identity'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { go, pageTitle, resolvePage, safeReturnTo, type Page } from './navigation'
import StoreLayout from './layouts/StoreLayout.vue'
import OperatorLayout from './layouts/OperatorLayout.vue'
import { user, login, register, logout, request, restore, explain } from './services/auth'
import Products from './views/Products.vue'
import Inventory from './views/Inventory.vue'
import Orders from './views/Orders.vue'
import Team from './views/Team.vue'
import Payment from './views/Payment.vue'
import OrderExceptions from './views/OrderExceptions.vue'
import RefundExceptions from './views/RefundExceptions.vue'
import Reconciliations from './views/Reconciliations.vue'
const page = ref<Page>(resolvePage(location.pathname)), routePath = ref(location.pathname)
const returnTo = ref(safeReturnTo(location.search))
function finishLogin() { go(returnTo.value ?? '/account', true); returnTo.value = null }
const loginName = ref(''), password = ref(''), displayName = ref('')
const busy = ref(true), error = ref(''), notice = ref('')
const operator = computed(() => user.value?.roles.includes('OPERATOR'))
const layout = computed(() => operator.value && ['admin','inventory','exceptions','refunds','reconciliations'].includes(page.value) ? OperatorLayout : StoreLayout)
function navigate(path: string) {
  const next = resolvePage(path)
  if ((next === 'login' || next === 'register') && returnTo.value) path += `?returnTo=${encodeURIComponent(returnTo.value)}`
  go(path); error.value = ''; notice.value = ''; password.value = ''
}
function pop() { page.value = resolvePage(location.pathname); routePath.value = location.pathname; returnTo.value = safeReturnTo(location.search); password.value = '' }
watch([page, routePath], () => { document.title = pageTitle(page.value) }, { immediate: true })
onMounted(async () => { window.addEventListener('popstate', pop); try { await restore(); if (user.value && ['login','register'].includes(page.value)) finishLogin() } catch (e) { error.value = explain(e) } finally { busy.value = false } })
onUnmounted(() => window.removeEventListener('popstate', pop))
async function submit() {
  if (busy.value) return
  const passwordLength = [...password.value].length
  if (passwordLength < 12 || passwordLength > 64) { error.value = '密码须为 12～64 个字符。'; return }
  busy.value = true; error.value = ''; notice.value = ''
  try {
    if (page.value === 'register') { await register(loginName.value, password.value, displayName.value); navigate('/login'); notice.value = '注册成功，请使用新账号登录。' }
    else { await login(loginName.value, password.value); password.value = ''; finishLogin() }
  } catch (e) { error.value = explain(e) } finally { password.value = ''; busy.value = false }
}
async function signOut() { busy.value = true; error.value = ''; try { await logout(); navigate('/login'); notice.value = '已退出登录。' } catch (e) { error.value = explain(e) } finally { busy.value = false } }
async function checkOperator() { busy.value = true; error.value = ''; try { const me = await request<User>('/admin/users/me'); notice.value = `${me.displayName}，运营身份验证成功。` } catch (e) { error.value = explain(e) } finally { busy.value = false } }
</script>
<template>
  <component :is="layout" :page="page" :signed-in="!!user" :operator="!!operator" @navigate="navigate">
    <main v-if="page==='products' || page==='admin'" class="catalog-main"><p v-if="error" class="message error" role="alert">{{ error }}</p><Products v-if="page!=='admin' || operator" :key="routePath" :admin="page==='admin'" /><p v-else role="alert">请使用运营账号登录后维护商品。</p></main>
    <main v-else-if="page==='team'" class="catalog-main"><Team :key="routePath" /></main>
    <main v-else-if="page==='payment'" class="catalog-main"><Payment :key="routePath" /></main>
    <main v-else-if="page==='orders'" class="catalog-main"><Orders :key="routePath" /></main>
    <main v-else-if="page==='exceptions'" class="catalog-main"><OrderExceptions v-if="operator" :key="routePath" /><p v-else role="alert">请使用运营账号登录后查看订单异常。</p></main>
    <main v-else-if="page==='refunds'" class="catalog-main"><RefundExceptions v-if="operator" :key="routePath" /><p v-else role="alert">请使用运营账号登录后查看退款。</p></main>
    <main v-else-if="page==='reconciliations'" class="catalog-main"><Reconciliations v-if="operator" :key="routePath" /><p v-else role="alert">请使用运营账号登录后查看完整核对。</p></main>
    <main v-else-if="page==='inventory'" class="catalog-main"><Inventory v-if="operator" /><p v-else role="alert">请使用运营账号登录后维护库存。</p></main>
    <main v-else-if="page==='not-found'" class="not-found"><p class="eyebrow">404 · 页面不存在</p><h1>没有找到这个页面</h1><p>地址可能已变化，请从商城首页重新选择。</p><a href="/" @click.prevent="navigate('/')">返回商城首页</a></main>
    <main v-else class="account-main">
      <section class="intro"><p class="eyebrow">正经商城 · 账号中心</p><h1>从这里，<br>开启你的商城体验。</h1><p>登录后查看你的账号信息。</p><div class="rule"></div><small>正经商城 · 账号中心</small></section>
      <section class="card" aria-labelledby="form-title">
        <template v-if="user">
          <p class="eyebrow">SIGNED IN</p><h2 id="form-title">你好，{{ user.displayName }}</h2><p class="muted">{{ user.loginName }}</p>
          <dl><dt>账号身份</dt><dd>{{ operator ? '用户 · 运营' : '普通用户' }}</dd><dt>账号编号</dt><dd class="id">{{ user.userId }}</dd></dl>
          <button v-if="operator" :disabled="busy" @click="checkOperator">验证运营权限</button>
          <button class="secondary" :disabled="busy" @click="signOut">{{ busy ? '处理中…' : '退出登录' }}</button>
        </template>
        <template v-else>
          <nav aria-label="账号操作"><button :class="{ active: page === 'login' }" @click="navigate('/login')">登录</button><button :class="{ active: page === 'register' }" @click="navigate('/register')">注册</button></nav>
          <h2 id="form-title">{{ page === 'register' ? '创建账号' : '欢迎回来' }}</h2><p class="muted">{{ page === 'register' ? '注册后，请使用你的账号登录。' : '输入账号与密码，继续访问。' }}</p>
          <form @submit.prevent="submit">
            <label for="loginName">登录名</label><input id="loginName" v-model="loginName" name="username" autocomplete="username" required minlength="3" maxlength="32" pattern="[a-z0-9][a-z0-9._-]{2,31}" :disabled="busy" placeholder="例如：market_user">
            <small>3～32 位小写字母、数字、点、下划线或短横线</small>
            <template v-if="page === 'register'"><label for="displayName">显示名称</label><input id="displayName" v-model="displayName" name="displayName" required maxlength="64" :disabled="busy" autocomplete="nickname"></template>
            <label for="password">密码</label><input id="password" v-model="password" name="password" type="password" :autocomplete="page === 'register' ? 'new-password' : 'current-password'" required minlength="12" maxlength="128" :disabled="busy"><small>12～64 个字符，区分大小写</small>
            <button class="primary" type="submit" :disabled="busy">{{ busy ? '处理中…' : page === 'register' ? '注册账号' : '登录' }}</button>
          </form>
        </template>
        <p v-if="error" class="message error" role="alert">{{ error }}</p><p v-if="notice" class="message notice" role="status">{{ notice }}</p>
      </section>
    </main>
  </component>
</template>
