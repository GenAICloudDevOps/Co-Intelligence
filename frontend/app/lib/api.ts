import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || ''

export const apiClient = axios.create({
  baseURL: API_URL,
  withCredentials: true,
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Surface API error messages consistently
    if (error?.response?.data?.detail) {
      error.message = error.response.data.detail
    }
    return Promise.reject(error)
  }
)

export async function login(email: string, password: string) {
  const res = await apiClient.post('/api/auth/login', { email, password })
  return res.data
}

export async function register(email: string, username: string, password: string | null, sendPasswordEmail = false) {
  const payload: Record<string, unknown> = { email, username, send_password_email: sendPasswordEmail }
  if (!sendPasswordEmail && password) {
    payload.password = password
  }
  const res = await apiClient.post('/api/auth/register', payload)
  return res.data
}

export async function requestPasswordReset(email: string) {
  const res = await apiClient.post('/api/auth/forgot-password', { email })
  return res.data
}

export async function resetPassword(token: string, password: string) {
  const res = await apiClient.post('/api/auth/reset-password', { token, password })
  return res.data
}
