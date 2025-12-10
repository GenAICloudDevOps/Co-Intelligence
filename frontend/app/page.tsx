'use client'

import React, { useState, useEffect } from 'react'
import AppCard from './components/AppCard'
import Modal from './components/Modal'
import { apps } from './config/apps'
import { useAuth } from './hooks/useAuth'
import { api } from './services/api'

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

export default function Home() {
  const { user, loading, message, setMessage, login, register, logout, isAuthenticated } = useAuth()
  const [showAuth, setShowAuth] = useState(false)
  const [isLogin, setIsLogin] = useState(true)
  const [formData, setFormData] = useState({ email: '', username: '', password: '' })
  const [currentTime, setCurrentTime] = useState('')
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [evalSummary, setEvalSummary] = useState<EvalSummary | null>(null)
  const [evalError, setEvalError] = useState<string | null>(null)
  const [evalScope, setEvalScope] = useState<'all' | 'me'>('all')

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
        await register(formData.email, formData.username, formData.password)
        setTimeout(() => {
          setShowAuth(false)
          setFormData({ email: '', username: '', password: '' })
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
    <div style={{ minHeight: '100vh', background: '#0f172a', color: 'white' }}>
      {/* Header */}
      <header style={{ padding: '16px 40px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)', background: '#1e293b' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '40px', height: '40px', background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '20px' }}>✨</div>
          <div>
            <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#a78bfa' }}>Co-Intelligence V3.0 Beta</div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>AI-Powered Applications</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '8px', height: '8px', background: '#10b981', borderRadius: '50%' }}></div>
            <span style={{ fontSize: '0.9rem', color: '#94a3b8' }}>Online</span>
          </div>
          <div style={{ fontSize: '0.9rem', color: '#94a3b8' }}>Updated: {currentTime}</div>
          {isAuthenticated ? (
            <>
              <div style={{ position: 'relative' }}>
                <button 
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  style={{ padding: '8px 16px', background: '#334155', borderRadius: '6px', fontSize: '0.9rem', border: 'none', color: 'white', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}
                >
                  👤 {user?.username || 'User'}
                </button>
                {showUserMenu && (
                  <div style={{ position: 'absolute', top: '45px', right: '0', background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', padding: '12px', minWidth: '200px', zIndex: 100 }}>
                    <div style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '8px' }}>
                      <div style={{ fontWeight: 'bold', color: 'white', marginBottom: '4px' }}>Username</div>
                      {user?.username || '—'}
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#94a3b8', paddingTop: '8px', borderTop: '1px solid #334155' }}>
                      <div style={{ fontWeight: 'bold', color: 'white', marginBottom: '4px' }}>Email</div>
                      {user?.email || '—'}
                    </div>
                  </div>
                )}
              </div>
              <button onClick={handleLogout} style={{ padding: '10px 24px', background: '#ef4444', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontWeight: '600' }}>🚪 Logout</button>
            </>
          ) : (
            <>
              <button onClick={() => { setShowAuth(true); setIsLogin(true); }} style={{ padding: '10px 24px', background: 'transparent', border: '1px solid #64748b', borderRadius: '6px', color: 'white', cursor: 'pointer' }}>Login</button>
              <button onClick={() => { setShowAuth(true); setIsLogin(false); }} style={{ padding: '10px 24px', background: '#10b981', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontWeight: '600' }}>Register</button>
            </>
          )}
        </div>
      </header>

      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '40px 40px' }}>
        {/* Hero Section */}
        <section style={{ textAlign: 'center', marginBottom: '30px' }}>
          <h1 style={{ fontSize: '4rem', fontWeight: 'bold', marginBottom: '12px', lineHeight: '1.2' }}>
            Where Human Meets<br/>
            <span style={{ background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>AI Intelligence</span>
          </h1>
          <p style={{ fontSize: '1.1rem', color: '#94a3b8', maxWidth: '900px', margin: '0 auto', lineHeight: '1.8' }}>
            <div style={{ textAlign: 'center' }}>Build once. Deploy to AWS, GCP, or Azure.</div>
            <div style={{ textAlign: 'center' }}>Agentic workflows • Serverless • Managed databases • Full-stack • Evals &amp; Guardrails</div>
          </p>
        </section>

        {/* AI Applications Section */}
        <section style={{ marginBottom: '80px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
            <h2 style={{ fontSize: '2rem', fontWeight: 'bold' }}>AI Applications</h2>
            <div style={{ display: 'flex', gap: '20px', fontSize: '0.9rem', color: '#64748b' }}>
              <span>⚡ {apps.filter(a => a.status === 'active').length} active</span>
              <span>🕐 Last updated: {currentTime}</span>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px' }}>
            {apps.map(app => (
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
          <div style={{ background: '#1e293b', borderRadius: '16px', padding: '50px', border: '1px solid #334155' }}>
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
                  background: '#0f172a',
                  borderRadius: '12px',
                  padding: '28px',
                  border: '1px solid #1e293b',
                  textAlign: 'center'
                }}>
                  <div style={{ width: '56px', height: '56px', background: feature.color, borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '28px', margin: '0 auto 20px' }}>{feature.icon}</div>
                  <h3 style={{ fontSize: '1.05rem', marginBottom: '12px', fontWeight: 'bold' }}>{feature.title}</h3>
                  <p style={{ color: '#64748b', lineHeight: '1.6', fontSize: '0.85rem' }}>
                    {feature.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Evaluation Dashboard (auth-gated) */}
        {isAuthenticated && (
          <section style={{ marginBottom: '60px' }}>
            <div style={{ background: '#0f172a', borderRadius: '16px', padding: '40px', border: '1px solid #334155' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
                <div>
                  <h2 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: '8px' }}>Evaluation Dashboard</h2>
                  <p style={{ color: '#94a3b8' }}>
                    Judge: {evalSummary?.judge_model || 'loading...'} • Last run: {evalSummary ? new Date(evalSummary.run_timestamp).toLocaleString() : '--'}
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                  <div style={{ color: '#94a3b8', fontSize: '0.95rem' }}>Total cases: {evalSummary?.total_cases ?? '--'}</div>
                  <div style={{ display: 'flex', gap: '8px', background: '#1e293b', padding: '6px', borderRadius: '10px', border: '1px solid #334155' }}>
                    {(['all', 'me'] as const).map(scope => (
                      <button
                        key={scope}
                        onClick={() => setEvalScope(scope)}
                        style={{
                          padding: '8px 12px',
                          borderRadius: '8px',
                          border: 'none',
                          background: evalScope === scope ? '#6366f1' : 'transparent',
                          color: evalScope === scope ? 'white' : '#94a3b8',
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
                <div style={{ background: '#1e293b', borderRadius: '12px', padding: '16px', border: '1px solid #334155', color: '#f97316', marginBottom: '12px' }}>
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
                  <div key={idx} style={{ background: '#1e293b', borderRadius: '12px', padding: '20px', border: '1px solid #334155' }}>
                    <div style={{ fontSize: '0.95rem', color: '#94a3b8', marginBottom: '8px', display: 'flex', justifyContent: 'space-between' }}>
                      <span>{metric.name}</span>
                      <span style={{ color: metric.delta >= 0 ? '#10b981' : '#ef4444' }}>
                        {metric.delta >= 0 ? '▲' : '▼'} {(metric.delta * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#a78bfa', marginBottom: '8px' }}>{(metric.score * 100).toFixed(0)}%</div>
                    <div style={{ background: '#0f172a', borderRadius: '999px', height: '10px', overflow: 'hidden', border: '1px solid #334155' }}>
                      <div style={{
                        width: `${Math.max(0, Math.min(100, metric.score * 100))}%`,
                        height: '100%',
                        background: 'linear-gradient(90deg, #22c55e, #a78bfa)'
                      }}></div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Safety and Model usage row */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '24px', alignItems: 'stretch' }}>
                <div style={{ background: '#1e293b', borderRadius: '12px', padding: '16px', border: '1px solid #334155' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ color: '#94a3b8', fontSize: '0.9rem' }}>Safety blocks (24h)</div>
                      <div style={{ fontSize: '1.8rem', fontWeight: 'bold', color: '#f97316' }}>{evalSummary?.safety_blocks?.count_24h ?? 0}</div>
                    </div>
                    <div style={{ color: (evalSummary?.safety_blocks?.change ?? 0) <= 0 ? '#10b981' : '#f97316' }}>
                      {(evalSummary?.safety_blocks?.change ?? 0) >= 0 ? '▲' : '▼'} {Math.abs(evalSummary?.safety_blocks?.change ?? 0)}
                    </div>
                  </div>
                </div>
                <div style={{ background: '#1e293b', borderRadius: '12px', padding: '16px', border: '1px solid #334155' }}>
                  <div style={{ color: '#94a3b8', marginBottom: '8px', fontSize: '0.95rem' }}>Model usage (top 5)</div>
                  {(evalSummary?.model_usage || []).map((m, idx) => (
                    <div key={idx} style={{ marginBottom: '6px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem', color: '#cbd5e1' }}>
                        <span>{m.model}</span>
                        <span style={{ color: '#94a3b8' }}>{m.count}</span>
                      </div>
                      <div style={{ background: '#0f172a', borderRadius: '999px', height: '8px', overflow: 'hidden', border: '1px solid #334155' }}>
                        <div style={{
                          width: `${Math.min(100, (m.count / Math.max(1, (evalSummary?.model_usage?.[0]?.count || 1))) * 100)}%`,
                          height: '100%',
                          background: '#22c55e'
                        }}></div>
                      </div>
                    </div>
                  ))}
                  {(evalSummary?.model_usage?.length ?? 0) === 0 && (
                    <div style={{ color: '#64748b' }}>No usage data yet.</div>
                  )}
                </div>
              </div>

              {/* Top issues */}
              <div style={{ background: '#1e293b', borderRadius: '12px', padding: '16px', border: '1px solid #334155', marginTop: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <h4 style={{ margin: 0, color: 'white' }}>Top issues</h4>
                  <span style={{ color: '#94a3b8', fontSize: '0.9rem', textAlign: 'center', width: '200px' }}>Lowest faithfulness/relevancy</span>
                </div>
                {(evalSummary?.issues || []).length === 0 ? (
                  <div style={{ color: '#64748b' }}>No issues yet.</div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: '2fr 2fr 1fr 1fr', gap: '8px', color: '#cbd5e1', fontSize: '0.9rem' }}>
                    <div style={{ color: '#94a3b8' }}>Prompt</div>
                    <div style={{ color: '#94a3b8' }}>Response</div>
                    <div style={{ color: '#94a3b8' }}>Faithfulness</div>
                    <div style={{ color: '#94a3b8' }}>Relevancy</div>
                    {(evalSummary?.issues || []).map((issue, idx) => (
                      <React.Fragment key={idx}>
                        <div>{issue.prompt || '—'}</div>
                        <div>{issue.response || '—'}</div>
                        <div style={{ color: issue.faithfulness < 0.6 ? '#f97316' : '#22c55e' }}>{(issue.faithfulness * 100).toFixed(0)}%</div>
                        <div style={{ color: issue.response_relevancy < 0.6 ? '#f97316' : '#22c55e' }}>{(issue.response_relevancy * 100).toFixed(0)}%</div>
                      </React.Fragment>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </section>
        )}

        {/* Platform Metrics Section */}
        <section style={{ marginBottom: '60px' }}>
          <div style={{ background: '#1e293b', borderRadius: '16px', padding: '50px', border: '1px solid #334155', textAlign: 'center' }}>
            <h2 style={{ fontSize: '2rem', marginBottom: '40px', fontWeight: 'bold' }}>Platform Metrics</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '40px', maxWidth: '800px', margin: '0 auto' }}>
              <div>
                <div style={{ fontSize: '3rem', fontWeight: 'bold', color: '#10b981', marginBottom: '8px' }}>7</div>
                <div style={{ fontSize: '1.1rem', color: '#94a3b8' }}>AI Models</div>
              </div>
              <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#f59e0b', marginBottom: '8px' }}>Role-Based Access</div>
                <div style={{ fontSize: '0.95rem', color: '#94a3b8' }}>Platform + App Roles</div>
              </div>
              <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#06b6d4', marginBottom: '8px' }}>Multi-Cloud</div>
                <div style={{ fontSize: '0.95rem', color: '#94a3b8' }}>AWS, GCP, Azure</div>
              </div>
              <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#6366f1', marginBottom: '8px' }}>Guardrails & Evaluation</div>
                <div style={{ fontSize: '0.95rem', color: '#94a3b8' }}>Safety blocks, metrics, issues</div>
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* Footer */}
      <footer style={{ background: '#0f172a', borderTop: '1px solid #1e293b', padding: '40px 0', textAlign: 'center' }}>
        <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '0 40px' }}>
          <div style={{ fontSize: '1.2rem', fontWeight: 'bold', marginBottom: '12px', color: '#a78bfa' }}>
            Co-Intelligence V3.0 Beta
          </div>
          <div style={{ fontSize: '0.95rem', color: '#64748b', marginBottom: '8px' }}>
            Built with ❤️ on AWS, GCP, Azure
          </div>
          <div style={{ fontSize: '0.85rem', color: '#475569' }}>
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
          onChange={(e) => setFormData({...formData, email: e.target.value})}
          style={{ width: '100%', padding: '12px', marginBottom: '15px', background: '#0f172a', border: '1px solid #334155', borderRadius: '6px', color: 'white' }} 
        />
        {!isLogin && (
          <input 
            type="text" 
            placeholder="Username" 
            value={formData.username}
            onChange={(e) => setFormData({...formData, username: e.target.value})}
            style={{ width: '100%', padding: '12px', marginBottom: '15px', background: '#0f172a', border: '1px solid #334155', borderRadius: '6px', color: 'white' }} 
          />
        )}
        <input 
          type="password" 
          placeholder="Password" 
          value={formData.password}
          onChange={(e) => setFormData({...formData, password: e.target.value})}
          onKeyPress={(e) => e.key === 'Enter' && handleAuth()}
          style={{ width: '100%', padding: '12px', marginBottom: '20px', background: '#0f172a', border: '1px solid #334155', borderRadius: '6px', color: 'white' }} 
        />
        {message && (
          <p style={{ marginBottom: '15px', color: message.includes('successful') ? '#10b981' : '#ef4444', textAlign: 'center' }}>
            {message}
          </p>
        )}
        <button 
          onClick={handleAuth}
          disabled={loading}
          style={{ width: '100%', padding: '12px', background: loading ? '#475569' : '#6366f1', border: 'none', borderRadius: '6px', color: 'white', fontSize: '1rem', cursor: loading ? 'not-allowed' : 'pointer', fontWeight: '600', marginBottom: '15px' }}
        >
          {loading ? 'Processing...' : (isLogin ? 'Login' : 'Register')}
        </button>
        <p style={{ textAlign: 'center', fontSize: '0.9rem', color: '#64748b' }}>
          {isLogin ? "Don't have an account? " : "Already have an account? "}
          <span onClick={() => { setIsLogin(!isLogin); setMessage(''); }} style={{ color: '#6366f1', cursor: 'pointer', textDecoration: 'underline' }}>
            {isLogin ? 'Register' : 'Login'}
          </span>
        </p>
      </Modal>
    </div>
  )
}
