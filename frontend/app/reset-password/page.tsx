'use client'

import React, { useMemo, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { authApi } from '../services/api'

const theme = {
  pageBg: '#0f172a',
  panelBg: '#1e293b',
  border: 'rgba(255,255,255,0.1)',
  text: '#e2e8f0',
  muted: '#94a3b8',
  accent: '#38bdf8',
  danger: '#ef4444',
  success: '#22c55e',
}

export default function ResetPasswordPage() {
  const searchParams = useSearchParams()
  const token = useMemo(() => searchParams.get('token') || '', [searchParams])

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setMessage('')
    setError('')

    if (!token) {
      setError('Reset token missing. Please use the link from your email.')
      return
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.')
      return
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setLoading(true)
    try {
      await authApi.resetPassword(token, password)
      setMessage('Password updated. You can log in now.')
      setPassword('')
      setConfirmPassword('')
    } catch (err: any) {
      setError(err?.message || 'Password reset failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: theme.pageBg, color: theme.text, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '40px 16px' }}>
      <div style={{ width: '100%', maxWidth: '420px', background: theme.panelBg, border: `1px solid ${theme.border}`, borderRadius: '16px', padding: '32px' }}>
        <h1 style={{ margin: '0 0 10px', fontSize: '1.6rem' }}>Reset Password</h1>
        <p style={{ margin: '0 0 20px', color: theme.muted, fontSize: '0.95rem' }}>
          Enter a new password for your account.
        </p>
        <form onSubmit={handleSubmit}>
          <input
            type="password"
            placeholder="New password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{ width: '100%', padding: '12px', marginBottom: '12px', background: '#0b1220', border: `1px solid ${theme.border}`, borderRadius: '8px', color: theme.text }}
          />
          <input
            type="password"
            placeholder="Confirm password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            style={{ width: '100%', padding: '12px', marginBottom: '14px', background: '#0b1220', border: `1px solid ${theme.border}`, borderRadius: '8px', color: theme.text }}
          />
          {message && (
            <div style={{ color: theme.success, marginBottom: '12px', fontSize: '0.9rem' }}>{message}</div>
          )}
          {error && (
            <div style={{ color: theme.danger, marginBottom: '12px', fontSize: '0.9rem' }}>{error}</div>
          )}
          <button
            type="submit"
            disabled={loading || !token}
            style={{
              width: '100%',
              padding: '12px',
              borderRadius: '8px',
              border: 'none',
              background: loading ? '#334155' : theme.accent,
              color: '#0b1220',
              fontWeight: 600,
              cursor: loading || !token ? 'not-allowed' : 'pointer',
              marginBottom: '12px',
            }}
          >
            {loading ? 'Updating...' : 'Update password'}
          </button>
        </form>
        <div style={{ textAlign: 'center' }}>
          <Link href="/" style={{ color: theme.muted, textDecoration: 'underline', fontSize: '0.9rem' }}>
            Back to login
          </Link>
        </div>
      </div>
    </div>
  )
}
