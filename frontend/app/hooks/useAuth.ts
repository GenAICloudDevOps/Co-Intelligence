import { useEffect, useMemo, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { login, register } from '../lib/api'

type AuthState = {
  id: number
  username: string
  email: string
  global_role?: string
  email_notifications_enabled?: boolean
}

export function useAuth(requireAuth = false) {
  const router = useRouter()
  const [auth, setAuth] = useState<AuthState | null>(null)
  const [loading, setLoading] = useState(false) // action-level loading
  const [initializing, setInitializing] = useState(true)
  const [message, setMessage] = useState('')
  const API_URL = useMemo(() => process.env.NEXT_PUBLIC_API_URL || '', [])

  const fetchCurrentUser = useCallback(async () => {
    setInitializing(true)
    try {
      const res = await fetch(`${API_URL}/api/auth/me`, { credentials: 'include' })
      if (!res.ok) throw new Error('Not authenticated')
      const data = await res.json()
      setAuth({
        id: data.id,
        username: data.username,
        email: data.email,
        global_role: data.global_role,
        email_notifications_enabled: !!data.email_notifications_enabled,
      })
      return data
    } catch (err) {
      setAuth(null)
      return null
    } finally {
      setInitializing(false)
    }
  }, [API_URL])

  useEffect(() => {
    fetchCurrentUser()
  }, [fetchCurrentUser])

  useEffect(() => {
    if (!initializing && requireAuth && !auth) {
      router.push('/')
    }
  }, [initializing, requireAuth, auth, router])

  const doLogin = async (email: string, password: string) => {
    setLoading(true)
    setMessage('')
    try {
      await login(email, password)
      await fetchCurrentUser()
      setMessage('Login successful!')
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || err.message || 'Authentication failed')
      throw err
    } finally {
      setLoading(false)
    }
  }

  const doRegister = async (email: string, username: string, password: string) => {
    setLoading(true)
    setMessage('')
    try {
      await register(email, username, password)
      await fetchCurrentUser()
      setMessage('Registration successful!')
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || err.message || 'Registration failed')
      throw err
    } finally {
      setLoading(false)
    }
  }

  const logout = async () => {
    try {
      await fetch(`${API_URL}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      })
    } catch {
      // ignore
    } finally {
      setAuth(null)
      if (requireAuth) router.push('/')
    }
  }

  return {
    auth,
    user: auth,
    loading,
    initializing,
    message,
    setMessage,
    login: doLogin,
    register: doRegister,
    logout,
    refresh: fetchCurrentUser,
    isAuthenticated: !!auth,
  }
}
