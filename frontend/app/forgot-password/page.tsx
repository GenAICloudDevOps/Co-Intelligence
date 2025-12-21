'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { authApi } from '../services/api'

const theme = {
  pageBg: '#0f172a',
  panelBg: '#1e293b',
  border: 'rgba(255,255,255,0.1)',
  text: '#e2e8f0',
  muted: '#94a3b8',
  accent: '#38bdf8',
  danger: '#ef4444',
}

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setMessage('')
    setError('')
    try {
      const res = await authApi.requestPasswordReset(email)
      setMessage(res?.message || 'If that email exists, a reset link has been sent.')
    } catch (err: any) {
      setError(err?.message || 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: theme.pageBg, color: theme.text, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '40px 16px' }}>
      <div style={{ width: '100%', maxWidth: '420px', background: theme.panelBg, border: `1px solid ${theme.border}`, borderRadius: '16px', padding: '32px' }}>
        <h1 style={{ margin: '0 0 10px', fontSize: '1.6rem' }}>Forgot Password</h1>
        <p style={{ margin: '0 0 20px', color: theme.muted, fontSize: '0.95rem' }}>
          Enter your email and we will send a reset link.
        </p>
        <form onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{ width: '100%', padding: '12px', marginBottom: '14px', background: '#0b1220', border: `1px solid ${theme.border}`, borderRadius: '8px', color: theme.text }}
          />
          {message && (
            <div style={{ color: theme.accent, marginBottom: '12px', fontSize: '0.9rem' }}>{message}</div>
          )}
          {error && (
            <div style={{ color: theme.danger, marginBottom: '12px', fontSize: '0.9rem' }}>{error}</div>
          )}
          <button
            type="submit"
            disabled={loading || !email}
            style={{
              width: '100%',
              padding: '12px',
              borderRadius: '8px',
              border: 'none',
              background: loading ? '#334155' : theme.accent,
              color: '#0b1220',
              fontWeight: 600,
              cursor: loading || !email ? 'not-allowed' : 'pointer',
              marginBottom: '12px',
            }}
          >
            {loading ? 'Sending...' : 'Send reset link'}
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
