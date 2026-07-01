import axios from 'axios'
import { useAuthStore } from '../stores/auth'

const client = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

client.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers.Authorization = 'Bearer ' + auth.token
  }
  return config
})

client.interceptors.response.use(
  (resp) => resp,
  (error) => {
    if (error.response && error.response.status === 401) {
      const auth = useAuthStore()
      auth.logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default client
