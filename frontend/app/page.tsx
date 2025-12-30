'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import AppCard from './design-system/components/AppCard'
import Modal from './design-system/components/Modal'
import ArchitectureDiagram from './components/ArchitectureDiagram'
import NotificationBell from './components/NotificationBell'
import NotificationPreferences from './components/NotificationPreferences'
import { apps } from './config/apps'
import { useAuth } from './hooks/useAuth'
import { api } from './services/api'
import { metaApi } from './services/meta'

type EvalMetric = { name: string; score: number; delta: number }
type TrendPoint = { label: string; context_precision: number; context_recall: number; response_relevancy: number; faithfulness: number }
type Issue = { prompt: string; response: string; faithfulness: number; response_relevancy: number; created_at: string; reason: string }
type ModelUsage = { model: string; count: number }
type EvalSummary = {
  run_id: string
  run_timestamp: string
  judge_model: string
  metrics: EvalMetric[]
  total_cases: number
  trend: TrendPoint[]
  issues: Issue[]
  safety_blocks: { count_24h: number; change: number }
  model_usage: ModelUsage[]
  scope: string
}

const observabilityLinks = [
  { name: 'Grafana', description: 'Dashboards and alerts', href: process.env.NEXT_PUBLIC_GRAFANA_URL || 'http://localhost:3000' },
  { name: 'Prometheus', description: 'Metrics and targets', href: process.env.NEXT_PUBLIC_PROMETHEUS_URL || 'http://localhost:9090' },
  { name: 'Jaeger', description: 'Tracing and latency', href: process.env.NEXT_PUBLIC_JAEGER_URL || 'http://localhost:16686' },
]

const themes = {
  default: {
    pageBg: '#0f172a',
    headerBg: '#1e293b',
    headerBorder: 'rgba(255,255,255,0.1)',
    panelBg: '#1e293b',
    panelAltBg: '#0f172a',
    border: '#334155',
    mutedText: '#94a3b8',
    softText: '#64748b',
    titleAccent: '#a78bfa',
    heroGradient: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
    brandGradient: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
    controlBg: '#334155',
    controlBorder: '#64748b',
    primaryButtonBg: '#10b981',
    dangerButtonBg: '#ef4444',
    success: '#10b981',
    warning: '#f97316',
    accent: '#6366f1',
    accentSoft: '#a78bfa',
    accentGradient: 'linear-gradient(90deg, #22c55e, #a78bfa)',
  },
  diwali: {
    pageBg: '#1b0c2e',
    headerBg: '#2a0f3f',
    headerBorder: 'rgba(255,255,255,0.12)',
    panelBg: '#241038',
    panelAltBg: '#1b0c2e',
    border: '#3b1a52',
    mutedText: '#f1c27d',
    softText: '#d49b5f',
    titleAccent: '#ffd166',
    heroGradient: 'linear-gradient(135deg, #ff7a00 0%, #ffb703 100%)',
    brandGradient: 'linear-gradient(135deg, #ff7a00 0%, #ffb703 100%)',
    controlBg: '#3b1a52',
    controlBorder: '#6b2d73',
    primaryButtonBg: '#ff7a00',
    dangerButtonBg: '#ef476f',
    success: '#06d6a0',
    warning: '#ffd166',
    accent: '#ff7a00',
    accentSoft: '#ffd166',
    accentGradient: 'linear-gradient(90deg, #ff7a00, #ffd166)',
  },
  christmas: {
    pageBg: '#0b1f1a',
    headerBg: '#113128',
    headerBorder: 'rgba(255,255,255,0.12)',
    panelBg: '#0f2a22',
    panelAltBg: '#0b1f1a',
    border: '#1f4a3d',
    mutedText: '#cfe7df',
    softText: '#9fc9ba',
    titleAccent: '#fef3c7',
    heroGradient: 'linear-gradient(135deg, #22c55e 0%, #ef4444 100%)',
    brandGradient: 'linear-gradient(135deg, #22c55e 0%, #ef4444 100%)',
    controlBg: '#1f4a3d',
    controlBorder: '#2b6b57',
    primaryButtonBg: '#ef4444',
    dangerButtonBg: '#b91c1c',
    success: '#22c55e',
    warning: '#f59e0b',
    accent: '#22c55e',
    accentSoft: '#fef3c7',
    accentGradient: 'linear-gradient(90deg, #22c55e, #fef3c7)',
  },
  newyear: {
    pageBg: '#0b1020',
    headerBg: '#121a33',
    headerBorder: 'rgba(255,255,255,0.12)',
    panelBg: '#121a33',
    panelAltBg: '#0b1020',
    border: '#223056',
    mutedText: '#c7d2fe',
    softText: '#94a3b8',
    titleAccent: '#f8fafc',
    heroGradient: 'linear-gradient(135deg, #38bdf8 0%, #a855f7 100%)',
    brandGradient: 'linear-gradient(135deg, #38bdf8 0%, #a855f7 100%)',
    controlBg: '#223056',
    controlBorder: '#37477a',
    primaryButtonBg: '#38bdf8',
    dangerButtonBg: '#ef4444',
    success: '#22c55e',
    warning: '#f59e0b',
    accent: '#38bdf8',
    accentSoft: '#a855f7',
    accentGradient: 'linear-gradient(90deg, #38bdf8, #a855f7)',
  },
}

type ThemeKey = keyof typeof themes

const themeStorageKey = 'coi-theme'

export default function Home() {
  const { user, loading, message, setMessage, login, register, logout, isAuthenticated, refresh } = useAuth()
  const [appCatalog, setAppCatalog] = useState(apps)
  const [cloudProvider, setCloudProvider] = useState<string | null>(null)
  const [showAuth, setShowAuth] = useState(false)
  const [isLogin, setIsLogin] = useState(true)
  const [formData, setFormData] = useState({ email: '', username: '', password: '' })
  const [sendPasswordEmail, setSendPasswordEmail] = useState(false)
  const [passwordForm, setPasswordForm] = useState({ current: '', next: '', confirm: '' })
  const [passwordStatus, setPasswordStatus] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [changingPassword, setChangingPassword] = useState(false)
  const [currentTime, setCurrentTime] = useState('')
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showChangePassword, setShowChangePassword] = useState(false)
  const [updatingEmailPrefs, setUpdatingEmailPrefs] = useState(false)
  const [evalSummary, setEvalSummary] = useState<EvalSummary | null>(null)
  const [evalError, setEvalError] = useState<string | null>(null)
  const [evalScope, setEvalScope] = useState<'all' | 'me'>('all')
  const [themeKey, setThemeKey] = useState<ThemeKey>('default')
  const theme = themes[themeKey]

  const handleToggleEmailNotifications = async () => {
    if (!user) return
    setUpdatingEmailPrefs(true)
    try {
      await api.put('/api/auth/me/preferences', {
        email_notifications_enabled: !user.email_notifications_enabled,
      })
      await refresh()
    } catch (e: any) {
      setMessage(e?.message || 'Failed to update email notifications')
    } finally {
      setUpdatingEmailPrefs(false)
    }
  }

  const handleToggleSlackNotifications = async () => {
    if (!user) return
    try {
      await api.put('/api/auth/me/preferences', {
        slack_notifications_enabled: !user.slack_notifications_enabled,
      })
      await refresh()
    } catch (e: any) {
      setMessage(e?.message || 'Failed to update Slack notifications')
    }
  }

  const handleChangePassword = async () => {
    if (!passwordForm.current || !passwordForm.next || !passwordForm.confirm) {
      setPasswordStatus({ type: 'error', text: 'Enter current and new password' })
      return
    }
    if (passwordForm.next.length < 6) {
      setPasswordStatus({ type: 'error', text: 'New password must be at least 6 characters' })
      return
    }
    if (passwordForm.next !== passwordForm.confirm) {
      setPasswordStatus({ type: 'error', text: 'New passwords do not match' })
      return
    }
    setChangingPassword(true)
    try {
      await api.put('/api/auth/me/password', {
        current_password: passwordForm.current,
        new_password: passwordForm.next,
      })
      setPasswordStatus({ type: 'success', text: 'Password updated' })
      setPasswordForm({ current: '', next: '', confirm: '' })
    } catch (e: any) {
      setPasswordStatus({ type: 'error', text: e?.message || 'Failed to update password' })
    } finally {
      setChangingPassword(false)
    }
  }

  useEffect(() => {
    const updateTime = () => {
      const now = new Date()
      setCurrentTime(now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }))
    }
    updateTime()
    const interval = setInterval(updateTime, 1000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const storedTheme = window.localStorage.getItem(themeStorageKey)
    if (storedTheme && storedTheme in themes) {
      setThemeKey(storedTheme as ThemeKey)
    }
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(themeStorageKey, themeKey)
  }, [themeKey])

  useEffect(() => {
    let active = true
    metaApi
      .getApps(false)
      .then((data) => {
        if (!active) return
        if (Array.isArray(data.apps) && data.apps.length) setAppCatalog(data.apps)
        if (data.cloudProvider) setCloudProvider(data.cloudProvider)
      })
      .catch(() => {
        // fallback to static catalog
      })
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    const fetchEvalSummary = async () => {
      if (!isAuthenticated) {
        setEvalSummary(null)
        return
      }
      try {
        const data = await api.get<EvalSummary>(`/api/apps/evaluations/summary?scope=${evalScope}`)
        setEvalSummary(data)
        setEvalError(null)
      } catch (err: any) {
        console.error('Eval fetch error', err)
        setEvalError('Evaluation data unavailable')
      }
    }
    fetchEvalSummary()
  }, [isAuthenticated, evalScope])

  const handleAuth = async () => {
    try {
      if (isLogin) {
        await login(formData.email, formData.password)
        setTimeout(() => {
          setShowAuth(false)
          setFormData({ email: '', username: '', password: '' })
        }, 800)
      } else {
        await register(
          formData.email,
          formData.username,
          sendPasswordEmail ? null : formData.password,
          sendPasswordEmail
        )
        setTimeout(() => {
          setShowAuth(false)
          setFormData({ email: '', username: '', password: '' })
          setSendPasswordEmail(false)
        }, 800)
      }
    } catch (error: any) {
      console.error('Auth error:', error)
    }
  }

  const handleLaunchChat = () => {
    if (!isAuthenticated) {
      setShowAuth(true)
      setIsLogin(true)
    } else {
      window.open('/apps/ai-chat', '_blank')
    }
  }

  const handleLogout = () => {
    logout()
  }

  return (
    <div style={{ minHeight: '100vh', background: theme.pageBg, color: 'white' }}>
      {/* Header */}
      <header style={{ padding: '16px 40px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: `1px solid ${theme.headerBorder}`, background: theme.headerBg }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '40px', height: '40px', background: theme.brandGradient, borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '20px' }}>✨</div>
          <div>
            <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: theme.titleAccent }}>Co-Intelligence V4.0 Beta</div>
            <div style={{ fontSize: '0.75rem', color: theme.mutedText }}>AI-Powered Applications</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '8px', height: '8px', background: theme.success, borderRadius: '50%' }}></div>
            <span style={{ fontSize: '0.9rem', color: theme.mutedText }}>Online</span>
          </div>
          <div style={{ fontSize: '0.9rem', color: theme.mutedText }}>Updated: {currentTime}</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.9rem', color: theme.mutedText }}>Theme</span>
            <select
              value={themeKey}
              onChange={(e) => setThemeKey(e.target.value as ThemeKey)}
              style={{
                background: theme.controlBg,
                color: 'white',
                border: `1px solid ${theme.controlBorder}`,
                borderRadius: '6px',
                padding: '8px 10px',
                fontSize: '0.9rem',
                cursor: 'pointer',
              }}
            >
              <option value="default">Default</option>
              <option value="diwali">Diwali</option>
              <option value="christmas">Christmas</option>
              <option value="newyear">Happy New Year</option>
            </select>
          </div>
          {isAuthenticated ? (
            <>
              <div style={{ position: 'relative' }}>
                <button
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  style={{ padding: '8px 16px', background: theme.controlBg, borderRadius: '6px', fontSize: '0.9rem', border: 'none', color: 'white', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}
                >
                  👤 {user?.username || 'User'}
                </button>
                {showUserMenu && (
                  <div
                    style={{
                      position: 'absolute',
                      top: '45px',
                      right: '0',
                      background: theme.panelBg,
                      border: `1px solid ${theme.border}`,
                      borderRadius: '8px',
                      padding: '12px',
                      width: 'min(640px, 92vw)',
                      zIndex: 100,
                    }}
                  >
                    <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                      <div style={{ flex: '0 1 340px', minWidth: '280px' }}>
                        <div style={{ fontSize: '0.85rem', color: theme.mutedText, marginBottom: '8px' }}>
                          <div style={{ fontWeight: 'bold', color: 'white', marginBottom: '4px' }}>Username</div>
                          {user?.username || '—'}
                        </div>
                        <div style={{ fontSize: '0.85rem', color: theme.mutedText, paddingTop: '8px', borderTop: `1px solid ${theme.border}` }}>
                          <div style={{ fontWeight: 'bold', color: 'white', marginBottom: '4px' }}>Email</div>
                          {user?.email || '—'}
                        </div>
                        <div style={{ fontSize: '0.85rem', color: theme.mutedText, paddingTop: '8px', borderTop: `1px solid ${theme.border}` }}>
                          <div style={{ fontWeight: 'bold', color: 'white', marginBottom: '4px' }}>Role</div>
                          {(() => {
                            const role = (user?.global_role || 'user').toLowerCase()
                            return role === 'user' ? 'User' : role.charAt(0).toUpperCase() + role.slice(1)
                          })()}
                        </div>
                        <div style={{ fontSize: '0.85rem', color: theme.mutedText, paddingTop: '8px', borderTop: `1px solid ${theme.border}` }}>
                          <button
                            type="button"
                            onClick={() => setShowChangePassword((prev) => !prev)}
                            aria-expanded={showChangePassword}
                            aria-controls="change-password-panel"
                            style={{
                              width: '100%',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'flex-start',
                              gap: '8px',
                              background: 'transparent',
                              border: 'none',
                              padding: '0 0 8px 0',
                              color: 'white',
                              cursor: 'pointer',
                              fontWeight: 'bold',
                              textAlign: 'left',
                            }}
                          >
                            <span style={{ color: theme.softText, fontSize: '0.9rem', width: '14px' }}>{showChangePassword ? '▾' : '▸'}</span>
                            <span>Change Password</span>
                          </button>
                          <div
                            id="change-password-panel"
                            aria-hidden={!showChangePassword}
                            style={{
                              marginTop: showChangePassword ? '8px' : '0',
                              maxHeight: showChangePassword ? '360px' : '0',
                              opacity: showChangePassword ? 1 : 0,
                              overflow: 'hidden',
                              pointerEvents: showChangePassword ? 'auto' : 'none',
                              transition: 'max-height 200ms ease, opacity 200ms ease, margin-top 200ms ease',
                            }}
                          >
                            <input
                              type="password"
                              placeholder="Current password"
                              value={passwordForm.current}
                              onChange={(e) => setPasswordForm({ ...passwordForm, current: e.target.value })}
                              disabled={!showChangePassword}
                              style={{
                                width: '100%',
                                padding: '8px',
                                marginBottom: '8px',
                                background: theme.panelAltBg,
                                border: `1px solid ${theme.border}`,
                                borderRadius: '6px',
                                color: 'white',
                              }}
                            />
                            <input
                              type="password"
                              placeholder="New password"
                              value={passwordForm.next}
                              onChange={(e) => setPasswordForm({ ...passwordForm, next: e.target.value })}
                              disabled={!showChangePassword}
                              style={{
                                width: '100%',
                                padding: '8px',
                                marginBottom: '8px',
                                background: theme.panelAltBg,
                                border: `1px solid ${theme.border}`,
                                borderRadius: '6px',
                                color: 'white',
                              }}
                            />
                            <input
                              type="password"
                              placeholder="Confirm new password"
                              value={passwordForm.confirm}
                              onChange={(e) => setPasswordForm({ ...passwordForm, confirm: e.target.value })}
                              disabled={!showChangePassword}
                              style={{
                                width: '100%',
                                padding: '8px',
                                marginBottom: '8px',
                                background: theme.panelAltBg,
                                border: `1px solid ${theme.border}`,
                                borderRadius: '6px',
                                color: 'white',
                              }}
                            />
                            {passwordStatus && (
                              <div style={{ fontSize: '0.75rem', marginBottom: '8px', color: passwordStatus.type === 'success' ? theme.success : theme.dangerButtonBg }}>
                                {passwordStatus.text}
                              </div>
                            )}
                            <button
                              onClick={handleChangePassword}
                              disabled={changingPassword || !showChangePassword}
                              style={{
                                width: '100%',
                                padding: '8px',
                                background: changingPassword ? theme.softText : theme.accent,
                                border: 'none',
                                borderRadius: '6px',
                                color: 'white',
                                cursor: changingPassword ? 'not-allowed' : 'pointer',
                                fontWeight: '600',
                              }}
                            >
                              {changingPassword ? 'Updating...' : 'Update Password'}
                            </button>
                          </div>
                        </div>
                        <NotificationPreferences
                          theme={theme}
                          globalEmailEnabled={!!user?.email_notifications_enabled}
                          globalSlackEnabled={!!user?.slack_notifications_enabled}
                        />
                      </div>

                      <div style={{ flex: '0 1 260px', minWidth: '220px', display: 'grid', gap: '12px' }}>
                        <div style={{
                          padding: '16px',
                          background: theme.panelAltBg,
                          borderRadius: '8px',
                          border: `1px solid ${theme.border}`
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                            <div style={{ fontWeight: 'bold', color: 'white' }}>Email Notifications</div>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                              <input
                                type="checkbox"
                                checked={!!user?.email_notifications_enabled}
                                onChange={handleToggleEmailNotifications}
                              />
                              <span style={{ color: 'white' }}>{user?.email_notifications_enabled ? 'On' : 'Off'}</span>
                            </label>
                          </div>

                          <div style={{ fontSize: '0.75rem', color: theme.softText, lineHeight: '1.4' }}>
                            <div>Master switch controls email delivery across all apps.</div>
                            <div style={{ marginTop: '12px', fontStyle: 'italic', opacity: 0.8 }}>
                              Note: In-app alerts have their own toggle.
                            </div>
                          </div>
                        </div>

                        <div style={{
                          padding: '16px',
                          background: theme.panelAltBg,
                          borderRadius: '8px',
                          border: `1px solid ${theme.border}`
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                            <div style={{ fontWeight: 'bold', color: 'white' }}>Slack Notifications</div>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                              <input
                                type="checkbox"
                                checked={!!user?.slack_notifications_enabled}
                                onChange={handleToggleSlackNotifications}
                              />
                              <span style={{ color: 'white' }}>{user?.slack_notifications_enabled ? 'On' : 'Off'}</span>
                            </label>
                          </div>

                          <div style={{ fontSize: '0.75rem', color: theme.softText, lineHeight: '1.4' }}>
                            <div>Master switch controls Slack delivery across all apps.</div>
                            <div style={{ marginTop: '12px', fontStyle: 'italic', opacity: 0.8 }}>
                              Per-app Slack toggles default to off.
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              <NotificationBell theme={theme} />
              <button onClick={handleLogout} style={{ padding: '10px 24px', background: theme.dangerButtonBg, border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontWeight: '600' }}>🚪 Logout</button>
            </>
          ) : (
            <>
              <button onClick={() => { setShowAuth(true); setIsLogin(true); }} style={{ padding: '10px 24px', background: 'transparent', border: `1px solid ${theme.controlBorder}`, borderRadius: '6px', color: 'white', cursor: 'pointer' }}>Login</button>
              <button onClick={() => { setShowAuth(true); setIsLogin(false); }} style={{ padding: '10px 24px', background: theme.primaryButtonBg, border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontWeight: '600' }}>Register</button>
            </>
          )}
        </div>
      </header>

      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '40px 40px' }}>
        {/* Hero Section */}
        <section style={{ textAlign: 'center', marginBottom: '30px' }}>
          <h1 style={{ fontSize: '4rem', fontWeight: 'bold', marginBottom: '12px', lineHeight: '1.2' }}>
            Where Human Meets<br />
            <span
              className="hero-gradient"
              style={{ '--hero-gradient': theme.heroGradient, '--hero-fallback': theme.titleAccent } as React.CSSProperties}
            >
              AI Intelligence
            </span>
          </h1>
          <p style={{ fontSize: '1.1rem', color: theme.mutedText, maxWidth: '900px', margin: '0 auto', lineHeight: '1.8' }}>
            <div style={{ textAlign: 'center' }}>Build once. Deploy to AWS, GCP, or Azure.</div>
            <div style={{ textAlign: 'center' }}>Agentic workflows • Serverless • Managed databases • Full-stack • Evals &amp; Guardrails</div>
          </p>
        </section>

        {/* AI Applications Section */}
        <section style={{ marginBottom: '80px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
            <h2 style={{ fontSize: '2rem', fontWeight: 'bold' }}>AI Applications</h2>
            <div style={{ display: 'flex', gap: '20px', fontSize: '0.9rem', color: theme.softText }}>
              <span>⚡ {appCatalog.filter(a => a.status === 'active').length} active</span>
              <span>🕐 Last updated: {currentTime}</span>
              {cloudProvider && <span>☁️ {cloudProvider.toUpperCase()}</span>}
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '24px' }}>
            {appCatalog.map(app => (
              <AppCard
                key={app.id}
                app={app}
                onLaunch={(app) => {
                  if (app.requiresAuth && !isAuthenticated) {
                    setShowAuth(true)
                    setIsLogin(true)
                  } else {
                    window.open(app.route, '_blank')
                  }
                }}
              />
            ))}
          </div>
        </section>

        {/* Platform Features Section */}
        <section style={{ marginBottom: '60px' }}>
          <div style={{ background: theme.panelBg, borderRadius: '16px', padding: '50px', border: `1px solid ${theme.border}` }}>
            <h2 style={{ fontSize: '2rem', marginBottom: '50px', textAlign: 'center', fontWeight: 'bold' }}>Platform Features</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '30px' }}>
              {[
                { icon: '☸️', title: 'Container Orchestration', desc: 'Kubernetes on any cloud with unified manifests', color: '#3b82f6' },
                { icon: '☁️', title: 'Multi-Cloud Ready', desc: 'Deploy anywhere - AWS, GCP, or Azure with cloud-agnostic infrastructure', color: '#ec4899' },
                { icon: '🐘', title: 'Managed Databases', desc: 'PostgreSQL on AWS RDS, GCP Cloud SQL, or Azure Flexible Server', color: '#8b5cf6' },
                { icon: '⚡', title: 'Serverless Execution', desc: 'Run code safely via AWS Lambda, GCP Cloud Functions, or Azure', color: '#f97316' },
                { icon: '🚀', title: 'Modern Full-Stack', desc: 'FastAPI + Next.js with SSR-ready APIs, streaming UX, and cookie-based auth', color: '#06b6d4' },
                { icon: '🔐', title: 'Secure Auth', desc: 'HttpOnly access/refresh cookies, rotation, session renewal, and RBAC', color: '#10b981' },
                { icon: '🧩', title: 'Modular Architecture', desc: 'Scalable, maintainable design with independent components', color: '#f59e0b' },
                { icon: '🤖', title: 'Multi-AI Support', desc: '7 AI models across 3 providers (Gemini, Groq, AWS Bedrock)', color: '#14b8a6' },
                { icon: '🔄', title: 'Agentic Workflows', desc: 'Multi-agent orchestration with state management and routing', color: '#ec4899' },
                { icon: '🛡️', title: 'Guardrails & Evaluation', desc: 'Auth-gated quality metrics, top issues, and safety', color: '#6366f1' }
              ].map((feature, idx) => (
                <div key={idx} style={{
                  background: theme.panelAltBg,
                  borderRadius: '12px',
                  padding: '28px',
                  border: `1px solid ${theme.border}`,
                  textAlign: 'center'
                }}>
                  <div style={{ width: '56px', height: '56px', background: feature.color, borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '28px', margin: '0 auto 20px' }}>{feature.icon}</div>
                  <h3 style={{ fontSize: '1.05rem', marginBottom: '12px', fontWeight: 'bold' }}>{feature.title}</h3>
                  <p style={{ color: theme.softText, lineHeight: '1.6', fontSize: '0.85rem' }}>
                    {feature.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Observability Section */}
        <section style={{ marginBottom: '60px' }}>
          <div style={{ background: theme.panelAltBg, borderRadius: '16px', padding: '40px', border: `1px solid ${theme.border}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: '16px', flexWrap: 'wrap', marginBottom: '20px' }}>
              <div>
                <h2 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: '8px' }}>Observability</h2>
                <p style={{ color: theme.mutedText }}>Monitor metrics, logs, and traces across the platform.</p>
              </div>
              <div style={{ color: theme.softText, fontSize: '0.9rem' }}>Prometheus • Grafana • Jaeger</div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
              {observabilityLinks.map((link) => (
                <a
                  key={link.name}
                  href={link.href}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    display: 'block',
                    background: theme.panelBg,
                    borderRadius: '12px',
                    padding: '18px',
                    border: `1px solid ${theme.border}`,
                    textDecoration: 'none',
                    color: 'white',
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: '6px' }}>{link.name}</div>
                  <div style={{ color: theme.softText, fontSize: '0.9rem', marginBottom: '10px' }}>{link.description}</div>
                  <div style={{ color: theme.accent, fontSize: '0.85rem' }}>Open →</div>
                </a>
              ))}
            </div>
          </div>
        </section>

        {/* Evaluation Dashboard (auth-gated) */}
        {isAuthenticated && (
          <section style={{ marginBottom: '60px' }}>
            <div style={{ background: theme.panelAltBg, borderRadius: '16px', padding: '40px', border: `1px solid ${theme.border}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
                <div>
                  <h2 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: '8px' }}>Evaluation Dashboard</h2>
                  <p style={{ color: theme.mutedText }}>
                    Judge: {evalSummary?.judge_model || 'loading...'} • Last run: {evalSummary ? new Date(evalSummary.run_timestamp).toLocaleString() : '--'}
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                  <div style={{ color: theme.mutedText, fontSize: '0.95rem' }}>Total cases: {evalSummary?.total_cases ?? '--'}</div>
                  <div style={{ display: 'flex', gap: '8px', background: theme.panelBg, padding: '6px', borderRadius: '10px', border: `1px solid ${theme.border}` }}>
                    {(['all', 'me'] as const).map(scope => (
                      <button
                        key={scope}
                        onClick={() => setEvalScope(scope)}
                        style={{
                          padding: '8px 12px',
                          borderRadius: '8px',
                          border: 'none',
                          background: evalScope === scope ? theme.accent : 'transparent',
                          color: evalScope === scope ? 'white' : theme.mutedText,
                          cursor: 'pointer',
                          fontWeight: 600
                        }}
                      >
                        {scope === 'all' ? 'All' : 'Me'}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              {evalError && (
                <div style={{ background: theme.panelBg, borderRadius: '12px', padding: '16px', border: `1px solid ${theme.border}`, color: theme.warning, marginBottom: '12px' }}>
                  {evalError}
                </div>
              )}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
                {(evalSummary?.metrics || [
                  { name: 'Context Precision', score: 0, delta: 0 },
                  { name: 'Context Recall', score: 0, delta: 0 },
                  { name: 'Response Relevancy', score: 0, delta: 0 },
                  { name: 'Faithfulness', score: 0, delta: 0 }
                ]).map((metric, idx) => (
                  <div key={idx} style={{ background: theme.panelBg, borderRadius: '12px', padding: '20px', border: `1px solid ${theme.border}` }}>
                    <div style={{ fontSize: '0.95rem', color: theme.mutedText, marginBottom: '8px', display: 'flex', justifyContent: 'space-between' }}>
                      <span>{metric.name}</span>
                      <span style={{ color: metric.delta >= 0 ? theme.success : theme.dangerButtonBg }}>
                        {metric.delta >= 0 ? '▲' : '▼'} {(metric.delta * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: theme.accentSoft, marginBottom: '8px' }}>{(metric.score * 100).toFixed(0)}%</div>
                    <div style={{ background: theme.panelAltBg, borderRadius: '999px', height: '10px', overflow: 'hidden', border: `1px solid ${theme.border}` }}>
                      <div style={{
                        width: `${Math.max(0, Math.min(100, metric.score * 100))}%`,
                        height: '100%',
                        background: theme.accentGradient
                      }}></div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Safety and Model usage row */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '24px', alignItems: 'stretch' }}>
                <div style={{ background: theme.panelBg, borderRadius: '12px', padding: '16px', border: `1px solid ${theme.border}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ color: theme.mutedText, fontSize: '0.9rem' }}>Safety blocks (24h)</div>
                      <div style={{ fontSize: '1.8rem', fontWeight: 'bold', color: theme.warning }}>{evalSummary?.safety_blocks?.count_24h ?? 0}</div>
                    </div>
                    <div style={{ color: (evalSummary?.safety_blocks?.change ?? 0) <= 0 ? theme.success : theme.warning }}>
                      {(evalSummary?.safety_blocks?.change ?? 0) >= 0 ? '▲' : '▼'} {Math.abs(evalSummary?.safety_blocks?.change ?? 0)}
                    </div>
                  </div>
                </div>
                <div style={{ background: theme.panelBg, borderRadius: '12px', padding: '16px', border: `1px solid ${theme.border}` }}>
                  <div style={{ color: theme.mutedText, marginBottom: '8px', fontSize: '0.95rem' }}>Model usage (top 5)</div>
                  {(evalSummary?.model_usage || []).map((m, idx) => (
                    <div key={idx} style={{ marginBottom: '6px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem', color: '#cbd5e1' }}>
                        <span>{m.model}</span>
                        <span style={{ color: theme.mutedText }}>{m.count}</span>
                      </div>
                      <div style={{ background: theme.panelAltBg, borderRadius: '999px', height: '8px', overflow: 'hidden', border: `1px solid ${theme.border}` }}>
                        <div style={{
                          width: `${Math.min(100, (m.count / Math.max(1, (evalSummary?.model_usage?.[0]?.count || 1))) * 100)}%`,
                          height: '100%',
                          background: theme.success
                        }}></div>
                      </div>
                    </div>
                  ))}
                  {(evalSummary?.model_usage?.length ?? 0) === 0 && (
                    <div style={{ color: theme.softText }}>No usage data yet.</div>
                  )}
                </div>
              </div>

              {/* Top issues */}
              <div style={{ background: theme.panelBg, borderRadius: '12px', padding: '16px', border: `1px solid ${theme.border}`, marginTop: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <h4 style={{ margin: 0, color: 'white' }}>Top issues</h4>
                  <span style={{ color: theme.mutedText, fontSize: '0.9rem', textAlign: 'center', width: '200px' }}>Lowest faithfulness/relevancy</span>
                </div>
                {(evalSummary?.issues || []).length === 0 ? (
                  <div style={{ color: theme.softText }}>No issues yet.</div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: '2fr 2fr 1fr 1fr', gap: '8px', color: '#cbd5e1', fontSize: '0.9rem' }}>
                    <div style={{ color: theme.mutedText }}>Prompt</div>
                    <div style={{ color: theme.mutedText }}>Response</div>
                    <div style={{ color: theme.mutedText }}>Faithfulness</div>
                    <div style={{ color: theme.mutedText }}>Relevancy</div>
                    {(evalSummary?.issues || []).map((issue, idx) => (
                      <React.Fragment key={idx}>
                        <div>{issue.prompt || '—'}</div>
                        <div>{issue.response || '—'}</div>
                        <div style={{ color: issue.faithfulness < 0.6 ? theme.warning : theme.success }}>{(issue.faithfulness * 100).toFixed(0)}%</div>
                        <div style={{ color: issue.response_relevancy < 0.6 ? theme.warning : theme.success }}>{(issue.response_relevancy * 100).toFixed(0)}%</div>
                      </React.Fragment>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </section>
        )}

        {/* Architecture Diagram Section */}
        <section style={{ marginBottom: '60px' }}>
          <div style={{ background: theme.panelAltBg, borderRadius: '16px', padding: '40px', border: `1px solid ${theme.border}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: '16px', flexWrap: 'wrap', marginBottom: '16px' }}>
              <div>
                <h2 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: '8px' }}>Architecture</h2>
                <p style={{ color: theme.mutedText }}>A quick, high-level view of how the UI, APIs, evals, and infrastructure fit together.</p>
              </div>
              <div style={{ color: theme.softText, fontSize: '0.9rem' }}>Multi-cloud • Modular • Auth-gated evals</div>
            </div>
            <ArchitectureDiagram />
          </div>
        </section>

        {/* Platform Metrics Section */}
        <section style={{ marginBottom: '60px' }}>
          <div style={{ background: theme.panelBg, borderRadius: '16px', padding: '50px', border: `1px solid ${theme.border}`, textAlign: 'center' }}>
            <h2 style={{ fontSize: '2rem', marginBottom: '40px', fontWeight: 'bold' }}>Platform Metrics</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '40px', maxWidth: '800px', margin: '0 auto' }}>
              <div>
                <div style={{ fontSize: '3rem', fontWeight: 'bold', color: theme.success, marginBottom: '8px' }}>7</div>
                <div style={{ fontSize: '1.1rem', color: theme.mutedText }}>AI Models</div>
              </div>
              <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: theme.warning, marginBottom: '8px' }}>Role-Based Access</div>
                <div style={{ fontSize: '0.95rem', color: theme.mutedText }}>Platform + App Roles</div>
              </div>
              <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: theme.accent, marginBottom: '8px' }}>Multi-Cloud</div>
                <div style={{ fontSize: '0.95rem', color: theme.mutedText }}>AWS, GCP, Azure</div>
              </div>
              <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: theme.accentSoft, marginBottom: '8px' }}>Guardrails & Evaluation</div>
                <div style={{ fontSize: '0.95rem', color: theme.mutedText }}>Safety blocks, metrics, issues</div>
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* Footer */}
      <footer style={{ background: theme.panelAltBg, borderTop: `1px solid ${theme.border}`, padding: '40px 0', textAlign: 'center' }}>
        <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '0 40px' }}>
          <div style={{ fontSize: '1.2rem', fontWeight: 'bold', marginBottom: '12px', color: theme.titleAccent }}>
            Co-Intelligence V4.0 Beta
          </div>
          <div style={{ fontSize: '0.95rem', color: theme.softText, marginBottom: '8px' }}>
            Built with ❤️ on AWS, GCP, Azure
          </div>
          <div style={{ fontSize: '0.85rem', color: theme.softText }}>
            © 2025 All rights reserved
          </div>
        </div>
      </footer>

      {/* Auth Modal */}
      <Modal isOpen={showAuth} onClose={() => setShowAuth(false)} title={isLogin ? 'Login' : 'Register'} maxWidth="400px">
        <input
          type="email"
          placeholder="Email"
          value={formData.email}
          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
          style={{ width: '100%', padding: '12px', marginBottom: '15px', background: theme.panelAltBg, border: `1px solid ${theme.border}`, borderRadius: '6px', color: 'white' }}
        />
        {!isLogin && (
          <input
            type="text"
            placeholder="Username"
            value={formData.username}
            onChange={(e) => setFormData({ ...formData, username: e.target.value })}
            style={{ width: '100%', padding: '12px', marginBottom: '15px', background: theme.panelAltBg, border: `1px solid ${theme.border}`, borderRadius: '6px', color: 'white' }}
          />
        )}
        {isLogin ? (
          <>
            <input
              type="password"
              placeholder="Password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              onKeyPress={(e) => e.key === 'Enter' && handleAuth()}
              style={{ width: '100%', padding: '12px', marginBottom: '10px', background: theme.panelAltBg, border: `1px solid ${theme.border}`, borderRadius: '6px', color: 'white' }}
            />
            <div style={{ textAlign: 'right', marginBottom: '20px' }}>
              <Link href="/forgot-password" style={{ fontSize: '0.85rem', color: theme.accent, textDecoration: 'underline' }}>
                Forgot password?
              </Link>
            </div>
          </>
        ) : (
          <>
            <input
              type="password"
              placeholder={sendPasswordEmail ? "Password will be emailed" : "Password"}
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              onKeyPress={(e) => e.key === 'Enter' && handleAuth()}
              disabled={sendPasswordEmail}
              style={{
                width: '100%',
                padding: '12px',
                marginBottom: '12px',
                background: theme.panelAltBg,
                border: `1px solid ${theme.border}`,
                borderRadius: '6px',
                color: 'white',
                opacity: sendPasswordEmail ? 0.6 : 1,
                cursor: sendPasswordEmail ? 'not-allowed' : 'text'
              }}
            />
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', color: theme.softText, marginBottom: '20px' }}>
              <input
                type="checkbox"
                checked={sendPasswordEmail}
                onChange={(e) => {
                  const checked = e.target.checked
                  setSendPasswordEmail(checked)
                  if (checked) setFormData({ ...formData, password: '' })
                }}
              />
              Email me a temporary password
            </label>
          </>
        )}
        {message && (
          <p style={{ marginBottom: '15px', color: message.includes('successful') ? theme.success : theme.dangerButtonBg, textAlign: 'center' }}>
            {message}
          </p>
        )}
        <button
          onClick={handleAuth}
          disabled={loading}
          style={{ width: '100%', padding: '12px', background: loading ? theme.softText : theme.accent, border: 'none', borderRadius: '6px', color: 'white', fontSize: '1rem', cursor: loading ? 'not-allowed' : 'pointer', fontWeight: '600', marginBottom: '15px' }}
        >
          {loading ? 'Processing...' : (isLogin ? 'Login' : 'Register')}
        </button>
        <p style={{ textAlign: 'center', fontSize: '0.9rem', color: theme.softText }}>
          {isLogin ? "Don't have an account? " : "Already have an account? "}
          <span
            onClick={() => {
              setIsLogin(!isLogin)
              setMessage('')
              setSendPasswordEmail(false)
              setFormData({ ...formData, password: '' })
            }}
            style={{ color: theme.accent, cursor: 'pointer', textDecoration: 'underline' }}
          >
            {isLogin ? 'Register' : 'Login'}
          </span>
        </p>
      </Modal>
      <style jsx>{`
        .hero-gradient {
          color: var(--hero-fallback);
        }

        @supports ((-webkit-background-clip: text) or (background-clip: text)) {
          .hero-gradient {
            background: var(--hero-gradient);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            -webkit-text-fill-color: transparent;
          }
        }
      `}</style>
    </div>
  )
}
