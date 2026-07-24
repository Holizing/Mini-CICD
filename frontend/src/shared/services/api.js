import axios from 'axios'

import { clearAuthToken, getAuthToken } from '../../modules/auth/authStorage'


const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = getAuthToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && getAuthToken()) {
      clearAuthToken()
      window.dispatchEvent(new Event('auth:unauthorized'))
    }
    return Promise.reject(error)
  },
)

export default api
