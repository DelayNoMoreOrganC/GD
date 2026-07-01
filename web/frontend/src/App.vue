<template>
  <div class="app-layout" v-if="auth.token">
    <el-container style="height: 100vh">
      <el-aside width="200px" class="sidebar">
        <div class="logo">案件归档</div>
        <el-menu :default-active="activeMenu" router class="side-menu">
          <el-menu-item index="/cases">
            <el-icon><Folder /></el-icon>
            <span>案件管理</span>
          </el-menu-item>
          <el-menu-item index="/settings" v-if="auth.isAdmin">
            <el-icon><Setting /></el-icon>
            <span>系统设置</span>
          </el-menu-item>
          <el-menu-item index="/admin" v-if="auth.isAdmin">
            <el-icon><UserFilled /></el-icon>
            <span>用户管理</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-container>
        <el-header class="topbar">
          <span class="case-title">{{ pageTitle }}</span>
          <el-dropdown>
            <span class="user-info">
              {{ auth.user ? auth.user.display_name : auth.user?.username }}
              <el-icon><CaretBottom /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="onLogout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </el-header>
        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
  <router-view v-else />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const activeMenu = computed(() => route.path)
const pageTitle = computed(() => {
  const map: Record<string, string> = {
    '/cases': '案件管理',
    '/settings': '系统设置',
    '/admin': '用户管理',
  }
  return map[route.path] || '案件归档系统'
})

function onLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style>
body { margin: 0; font-family: -apple-system, 'Microsoft YaHei', sans-serif; }
.sidebar { background: #1d2129; color: #e5eaf3; }
.logo { height: 60px; line-height: 60px; text-align: center; font-size: 18px; font-weight: 600; color: #fff; }
.side-menu { border-right: none; background: transparent; }
.side-menu .el-menu-item { color: #c9d1d9; }
.side-menu .el-menu-item.is-active { background: #2a6cf6; color: #fff; }
.topbar { display: flex; align-items: center; justify-content: space-between; background: #fff; border-bottom: 1px solid #e5e6eb; }
.case-title { font-size: 16px; font-weight: 600; color: #1d2129; }
.user-info { cursor: pointer; color: #4e5969; display: flex; align-items: center; gap: 4px; }
</style>
