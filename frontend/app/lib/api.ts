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

export async function register(email: string, username: string, password: string) {
  const res = await apiClient.post('/api/auth/register', { email, username, password })
  return res.data
}
