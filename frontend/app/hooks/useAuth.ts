'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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
    const username = localStorage.getItem('username')
    const email = localStorage.getItem('email')

    if (!storedToken) {
      setLoading(false)
      if (requireAuth) {
        router.push('/')
      }
      return
    }

    setToken(storedToken)

    // Fetch user from backend
    fetch(`${API_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${storedToken}` }
    })
      .then(res => {
        if (!res.ok) throw new Error('Unauthorized')
        return res.json()
      })
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

  const logout = () => {
    localStorage.clear()
    setUser(null)
    setToken(null)
    router.push('/')
  }

  return { user, loading, token, logout, isAuthenticated: !!user }
}
