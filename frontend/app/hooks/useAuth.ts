import { useEffect, useState } from 'react'
import { login, register } from '../lib/api'

type AuthState = {
  token: string
  username: string
  email: string
}

export function useAuth(requireAuth = false) {
  const [auth, setAuth] = useState<AuthState>({ token: '', username: '', email: '' })
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (typeof window === 'undefined') return
    const token = localStorage.getItem('token') || ''
    const username = localStorage.getItem('username') || ''
    const email = localStorage.getItem('email') || ''
    setAuth({ token, username, email })
  }, [])

  const doLogin = async (email: string, password: string) => {
    setLoading(true)
    setMessage('')
    try {
      const data = await login(email, password)
      persistAuth({
        token: data.access_token,
        refresh: data.refresh_token,
        username: email.split('@')[0],
        email,
      })
      setMessage('Login successful!')
    } catch (err: any) {
      setMessage(err.message || 'Authentication failed')
      throw err
    } finally {
      setLoading(false)
    }
  }

  const doRegister = async (email: string, username: string, password: string) => {
    setLoading(true)
    setMessage('')
    try {
      const data = await register(email, username, password)
      persistAuth({
        token: data.access_token,
        refresh: data.refresh_token,
        username,
        email,
      })
      setMessage('Registration successful!')
    } catch (err: any) {
      setMessage(err.message || 'Registration failed')
      throw err
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('username')
      localStorage.removeItem('email')
    }
    setAuth({ token: '', username: '', email: '' })
  }

  const persistAuth = ({
    token,
    refresh,
    username,
    email,
  }: {
    token: string
    refresh: string
    username: string
    email: string
  }) => {
    if (typeof window === 'undefined') return
    localStorage.setItem('token', token)
    localStorage.setItem('refresh_token', refresh)
    localStorage.setItem('username', username)
    localStorage.setItem('email', email)
    setAuth({ token, username, email })
  }

  return {
    auth,
    user: auth.token ? auth : null,
    loading,
    message,
    setMessage,
    login: doLogin,
    register: doRegister,
    logout,
    isAuthenticated: !!auth.token,
  }
}
