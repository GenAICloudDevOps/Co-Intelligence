'use client'

import { useRouter } from 'next/navigation'
import { useState, useEffect } from 'react'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Home() {
  const router = useRouter()
  const [showAuth, setShowAuth] = useState(false)
  const [isLogin, setIsLogin] = useState(true)
  const [token, setToken] = useState('')
  const [username, setUsername] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [formData, setFormData] = useState({ email: '', username: '', password: '' })
  const [currentTime, setCurrentTime] = useState('')
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [userEmail, setUserEmail] = useState('')

  useEffect(() => {
    const savedToken = localStorage.getItem('token')
    const savedUsername = localStorage.getItem('username')
    const savedEmail = localStorage.getItem('email')
    if (savedToken) setToken(savedToken)
    if (savedUsername) setUsername(savedUsername)
    if (savedEmail) setUserEmail(savedEmail)
    
    const updateTime = () => {
      const now = new Date()
      setCurrentTime(now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }))
    }
    updateTime()
    const interval = setInterval(updateTime, 1000)
    return () => clearInterval(interval)
  }, [])

  const handleAuth = async () => {
    setLoading(true)
    setMessage('')
    try {
      if (isLogin) {
        const response = await axios.post(`${API_URL}/api/auth/login`, {
          email: formData.email,
          password: formData.password
        })
        const newToken = response.data.access_token
        setToken(newToken)
        localStorage.setItem('token', newToken)
        localStorage.setItem('username', formData.email.split('@')[0])
        localStorage.setItem('email', formData.email)
        setUsername(formData.email.split('@')[0])
        setUserEmail(formData.email)
        setMessage('Login successful!')
        setTimeout(() => {
          setShowAuth(false)
          setFormData({ email: '', username: '', password: '' })
        }, 1000)
      } else {
        const response = await axios.post(`${API_URL}/api/auth/register`, {
          email: formData.email,
          username: formData.username,
          password: formData.password
        })
        const newToken = response.data.access_token
        setToken(newToken)
        localStorage.setItem('token', newToken)
        localStorage.setItem('username', formData.username)
        localStorage.setItem('email', formData.email)
        setUsername(formData.username)
        setUserEmail(formData.email)
        setMessage('Registration successful!')
        setTimeout(() => {
          setShowAuth(false)
          setFormData({ email: '', username: '', password: '' })
        }, 1000)
      }
    } catch (error: any) {
      console.error('Auth error:', error.response?.data)
      setMessage(error.response?.data?.detail || 'Authentication failed')
    }
    setLoading(false)
  }

  const handleLaunchChat = () => {
    if (!token) {
      setShowAuth(true)
      setIsLogin(true)
    } else {
      window.open('/apps/ai-chat', '_blank')
    }
  }

  const handleLogout = () => {
    setToken('')
    setUsername('')
    setUserEmail('')
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('email')
  }

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a', color: 'white' }}>
      {/* Header */}
      <header style={{ padding: '16px 40px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)', background: '#1e293b' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '40px', height: '40px', background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '20px' }}>✨</div>
          <div>
            <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#a78bfa' }}>Co-Intelligence V1.0 Beta</div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>AI-Powered Applications</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '8px', height: '8px', background: '#10b981', borderRadius: '50%' }}></div>
            <span style={{ fontSize: '0.9rem', color: '#94a3b8' }}>Online</span>
          </div>
          <div style={{ fontSize: '0.9rem', color: '#94a3b8' }}>Updated: {currentTime}</div>
          {token ? (
            <>
              <div style={{ position: 'relative' }}>
                <button 
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  style={{ padding: '8px 16px', background: '#334155', borderRadius: '6px', fontSize: '0.9rem', border: 'none', color: 'white', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}
                >
                  👤 {username}
                </button>
                {showUserMenu && (
                  <div style={{ position: 'absolute', top: '45px', right: '0', background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', padding: '12px', minWidth: '200px', zIndex: 100 }}>
                    <div style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '8px' }}>
                      <div style={{ fontWeight: 'bold', color: 'white', marginBottom: '4px' }}>Username</div>
                      {username}
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#94a3b8', paddingTop: '8px', borderTop: '1px solid #334155' }}>
                      <div style={{ fontWeight: 'bold', color: 'white', marginBottom: '4px' }}>Email</div>
                      {userEmail}
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
        <section style={{ textAlign: 'center', marginBottom: '40px' }}>
          <h1 style={{ fontSize: '4.5rem', fontWeight: 'bold', marginBottom: '16px', lineHeight: '1.2' }}>
            Where Human Meets<br/>
            <span style={{ background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>AI Intelligence</span>
          </h1>
          <p style={{ fontSize: '1.1rem', color: '#94a3b8', maxWidth: '900px', margin: '0 auto', lineHeight: '1.8' }}>
            A modular, container orchestration platform for rapid co-intelligence development
          </p>
        </section>

        {/* AI Applications Section */}
        <section style={{ marginBottom: '80px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
            <h2 style={{ fontSize: '2rem', fontWeight: 'bold' }}>AI Applications</h2>
            <div style={{ display: 'flex', gap: '20px', fontSize: '0.9rem', color: '#64748b' }}>
              <span>⚡ 2 active</span>
              <span>🕐 Last updated: {currentTime}</span>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '24px' }}>
            <div style={{
              background: '#1e293b',
              borderRadius: '12px',
              padding: '32px',
              border: '1px solid #334155',
              position: 'relative'
            }}>
              <div style={{ position: 'absolute', top: '20px', right: '20px', padding: '4px 12px', background: '#10b981', borderRadius: '12px', fontSize: '0.75rem', fontWeight: '600' }}>active</div>
              <div style={{ width: '48px', height: '48px', background: '#6366f1', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '24px', marginBottom: '20px' }}>💬</div>
              <h3 style={{ fontSize: '1.5rem', marginBottom: '12px', fontWeight: 'bold' }}>Chat</h3>
              <p style={{ color: '#94a3b8', lineHeight: '1.6', marginBottom: '24px', fontSize: '0.95rem' }}>
                • AI Chat<br/>
                • Document Analysis<br/>
                • Web Search<br/>
                • Code Execution
              </p>
              <button onClick={handleLaunchChat} style={{ padding: '12px 28px', background: '#6366f1', border: 'none', borderRadius: '8px', color: 'white', cursor: 'pointer', fontWeight: '600', fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                Launch <span>↗</span>
              </button>
            </div>

            <div style={{
              background: '#1e293b',
              borderRadius: '12px',
              padding: '32px',
              border: '1px solid #334155',
              position: 'relative'
            }}>
              <div style={{ position: 'absolute', top: '20px', right: '20px', padding: '4px 12px', background: '#10b981', borderRadius: '12px', fontSize: '0.75rem', fontWeight: '600' }}>active</div>
              <div style={{ width: '48px', height: '48px', background: '#f97316', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '24px', marginBottom: '20px' }}>☕</div>
              <h3 style={{ fontSize: '1.5rem', marginBottom: '12px', fontWeight: 'bold' }}>Agentic Barista</h3>
              <p style={{ color: '#94a3b8', lineHeight: '1.6', marginBottom: '24px', fontSize: '0.95rem' }}>
                • Natural Language Ordering<br/>
                • Menu Discovery<br/>
                • Smart Cart Management<br/>
                • Order Confirmation
              </p>
              <button onClick={() => window.open('/apps/agentic-barista', '_blank')} style={{ padding: '12px 28px', background: '#f97316', border: 'none', borderRadius: '8px', color: 'white', cursor: 'pointer', fontWeight: '600', fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                Launch <span>↗</span>
              </button>
            </div>
          </div>
        </section>

        {/* Platform Features Section */}
        <section>
          <div style={{ background: '#1e293b', borderRadius: '16px', padding: '50px', border: '1px solid #334155' }}>
            <h2 style={{ fontSize: '2rem', marginBottom: '50px', textAlign: 'center', fontWeight: 'bold' }}>Platform Features</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '30px' }}>
              {[
                { icon: '☸️', title: 'Kubernetes (AWS EKS)', desc: 'Container orchestration with auto-scaling and health monitoring', color: '#3b82f6' },
                { icon: '⚡', title: 'FastAPI Backend', desc: 'High-performance async Python API with automatic documentation', color: '#f97316' },
                { icon: '▲', title: 'Next.js Frontend', desc: 'Next.js 14 App Router with server-side rendering and optimized builds', color: '#06b6d4' },
                { icon: '🐘', title: 'PostgreSQL Database', desc: 'Reliable AWS RDS with Tortoise ORM and automated migrations', color: '#8b5cf6' },
                { icon: '🔐', title: 'JWT Authentication', desc: 'Secure user registration, login, and session management', color: '#10b981' },
                { icon: '☁️', title: 'AI/Cloud First', desc: 'Built for AWS with intelligent automation and cloud-native architecture', color: '#ec4899' },
                { icon: '🧩', title: 'Modular Architecture', desc: 'Scalable, maintainable design with independent components', color: '#f59e0b' },
                { icon: '🤝', title: 'Co-Intelligence', desc: 'Collaborative intelligence combining human insight and AI capabilities', color: '#6366f1' }
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
      </div>

      {/* Auth Modal */}
      {showAuth && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }} onClick={() => setShowAuth(false)}>
          <div style={{ background: '#1e293b', padding: '40px', borderRadius: '16px', width: '400px', maxWidth: '90%', border: '1px solid #334155' }} onClick={(e) => e.stopPropagation()}>
            <h2 style={{ marginBottom: '30px', fontSize: '1.8rem' }}>{isLogin ? 'Login' : 'Register'}</h2>
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
          </div>
        </div>
      )}
    </div>
  )
}
