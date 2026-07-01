import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('../views/Login.vue') },
    { path: '/', redirect: '/cases' },
    { path: '/cases', name: 'cases', component: () => import('../views/Dashboard.vue') },
    { path: '/cases/:id', name: 'case-detail', component: () => import('../views/CaseDetail.vue') },
    { path: '/cases/:id/tasks/:taskId', name: 'task', component: () => import('../views/TaskProgress.vue') },
    { path: '/settings', name: 'settings', component: () => import('../views/Settings.vue') },
    { path: '/admin', name: 'admin', component: () => import('../views/Admin.vue') },
  ],
})

router.beforeEach((to, _from, next) => {
  const auth = useAuthStore()
  if (to.name !== 'login' && !auth.token) {
    next({ name: 'login' })
  } else {
    next()
  }
})

export default router
