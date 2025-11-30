'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { api } from '../services/api'

interface User {
  id: number
  email: string
  username: string
}

export function useAuth(requireAuth: boolean = true) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [token, setToken] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    const storedToken = localStorage.getItem('token')

    if (!storedToken) {
      setLoading(false)
      if (requireAuth) {
        router.push('/')
      }
      return
    }

    setToken(storedToken)

    api.get<User>('/api/auth/me')
      .then(data => {
        setUser(data)
        setLoading(false)
      })
      .catch(() => {
        localStorage.clear()
        setLoading(false)
        if (requireAuth) {
          router.push('/')
        }
      })
  }, [requireAuth, router])

  const logout = async () => {
    try {
      await api.post('/api/auth/logout')
    } catch {
      // Ignore errors, clear anyway
    }
    localStorage.clear()
    setUser(null)
    setToken(null)
    router.push('/')
  }

  return { user, loading, token, logout, isAuthenticated: !!user }
}
