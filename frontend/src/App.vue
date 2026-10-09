<script setup lang="ts">
import type { User } from './types/identity'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { user, login, register, logout, request, restore, explain } from './services/auth'
import Products from './views/Products.vue'
function route() { return location.pathname.startsWith('/admin/products') ? 'admin' : location.pathname === '/' || location.pathname.startsWith('/products') ? 'products' : location.pathname === '/register' ? 'register' : 'login' }
const page = ref(route()), routePath = ref(location.pathname)
function safeReturn() {
  const path = new URLSearchParams(location.search).get('returnTo')
  return path && /^(?:\/|\/products(?:\/[A-Za-z0-9._-]{1,64})?)$/.test(path) ? path : null
}
const returnTo = ref(safeReturn())
function finishLogin() { if (returnTo.value) { history.replaceState(null, '', returnTo.value); returnTo.value = null; routePath.value = location.pathname; page.value = route() } }
const loginName = ref(''), password = ref(''), displayName = ref('')
const busy = ref(true), error = ref(''), notice = ref('')
const operator = computed(() => user.value?.roles.includes('OPERATOR'))
function navigate(next: string) { page.value = next; if (!['login','register'].includes(next)) returnTo.value = null; history.pushState(null, '', (next === 'admin' ? '/admin/products' : `/${next}`) + (['login','register'].includes(next) && returnTo.value ? `?returnTo=${encodeURIComponent(returnTo.value)}` : '')); routePath.value = location.pathname; error.value = ''; notice.value = ''; password.value = '' }
function pop() { page.value = route(); routePath.value = location.pathname; returnTo.value = safeReturn(); password.value = '' }
onMounted(async () => { window.addEventListener('popstate', pop); try { await restore(); if (user.value) finishLogin() } catch (e) { error.value = explain(e) } finally { busy.value = false } })
onUnmounted(() => window.removeEventListener('popstate', pop))
async function submit() {
  if (busy.value) return
  const passwordLength = [...password.value].length
  if (passwordLength < 12 || passwordLength > 64) { error.value = '密码须为 12～64 个字符。'; return }
  busy.value = true; error.value = ''; notice.value = ''
  try {
    if (page.value === 'register') { await register(loginName.value, password.value, displayName.value); navigate('login'); notice.value = '注册成功，请使用新账号登录。' }
    else { await login(loginName.value, password.value); password.value = ''; finishLogin() }
  } catch (e) { error.value = explain(e) } finally { password.value = ''; busy.value = false }
}
async function signOut() { busy.value = true; error.value = ''; try { await logout(); notice.value = '已退出登录。' } catch (e) { error.value = explain(e) } finally { busy.value = false } }
async function checkOperator() { busy.value = true; error.value = ''; try { const me = await request<User>('/admin/users/me'); notice.value = `${me.displayName}，运营身份验证成功。` } catch (e) { error.value = explain(e) } finally { busy.value = false } }
</script>
<template>
  <div class="shell">
    <header><a href="/login" @click.prevent="navigate('login')" class="brand">知集 <span>MARKET</span></a><nav class="site-nav"><button @click="navigate('products')">商城商品</button><button v-if="operator" @click="navigate('admin')">商品管理</button><button @click="navigate('login')">账号中心</button></nav></header>
    <main v-if="page==='products' || page==='admin'" class="catalog-main"><p v-if="error" class="message error" role="alert">{{ error }}</p><Products v-if="page!=='admin' || operator" :key="routePath" :admin="page==='admin'" /><p v-else role="alert">请使用运营账号登录后维护商品。</p></main>
    <main v-else>
      <section class="intro"><p class="eyebrow">YOUR ACCOUNT</p><h1>从这里，<br>开启你的商城体验。</h1><p>登录后查看你的账号信息。</p><div class="rule"></div><small>知集商城 · 账号中心</small></section>
      <section class="card" aria-labelledby="form-title">
        <template v-if="user">
          <p class="eyebrow">SIGNED IN</p><h2 id="form-title">你好，{{ user.displayName }}</h2><p class="muted">{{ user.loginName }}</p>
          <dl><dt>账号身份</dt><dd>{{ operator ? '用户 · 运营' : '普通用户' }}</dd><dt>账号编号</dt><dd class="id">{{ user.userId }}</dd></dl>
          <button v-if="operator" :disabled="busy" @click="checkOperator">验证运营权限</button>
          <button class="secondary" :disabled="busy" @click="signOut">{{ busy ? '处理中…' : '退出登录' }}</button>
        </template>
        <template v-else>
          <nav aria-label="账号操作"><button :class="{ active: page === 'login' }" @click="navigate('login')">登录</button><button :class="{ active: page === 'register' }" @click="navigate('register')">注册</button></nav>
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
    </main><footer>知集商城</footer>
  </div>
</template>
