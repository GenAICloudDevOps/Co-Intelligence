import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { authApi } from '../services/api'

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

  const fetchCurrentUser = useCallback(async () => {
    setInitializing(true)
    try {
      const data = await authApi.me()
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
  }, [])

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
      await authApi.login(email, password)
      await fetchCurrentUser()
      setMessage('Login successful!')
    } catch (err: any) {
      setMessage(err?.message || 'Authentication failed')
      throw err
    } finally {
      setLoading(false)
    }
  }

  const doRegister = async (email: string, username: string, password: string) => {
    setLoading(true)
    setMessage('')
    try {
      await authApi.register(email, username, password)
      await fetchCurrentUser()
      setMessage('Registration successful!')
    } catch (err: any) {
      setMessage(err?.message || 'Registration failed')
      throw err
    } finally {
      setLoading(false)
    }
  }

  const logout = async () => {
    try {
      await authApi.logout()
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
