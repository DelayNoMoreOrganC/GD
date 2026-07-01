import { defineStore } from 'pinia'
import client from '../api/client'

interface UserInfo {
  id: string
  username: string
  display_name: string
  role: string
  org_id: string
  is_active: boolean
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('v5_token') || '',
    refreshToken: localStorage.getItem('v5_refresh') || '',
    user: JSON.parse(localStorage.getItem('v5_user') || 'null') as UserInfo | null,
  }),
  getters: {
    isAdmin: (state) => state.user?.role === 'admin',
  },
  actions: {
    async login(username: string, password: string) {
      const { data } = await client.post('/auth/login', { username, password })
      this.token = data.access_token
      this.refreshToken = data.refresh_token
      localStorage.setItem('v5_token', this.token)
      localStorage.setItem('v5_refresh', this.refreshToken)
      await this.fetchMe()
    },
    async fetchMe() {
      const { data } = await client.get('/auth/me')
      this.user = data
      localStorage.setItem('v5_user', JSON.stringify(data))
    },
    logout() {
      this.token = ''
      this.refreshToken = ''
      this.user = null
      localStorage.removeItem('v5_token')
      localStorage.removeItem('v5_refresh')
      localStorage.removeItem('v5_user')
    },
  },
})
