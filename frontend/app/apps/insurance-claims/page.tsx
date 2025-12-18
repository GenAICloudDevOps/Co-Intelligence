'use client'

import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { ModelSelector } from '../../config/models'
import { useModel } from '../../components/ModelProvider'
import { api } from '../../services/api'
import { useAuth } from '../../hooks/useAuth'
import { useSpeechToText } from '../../hooks/useSpeechToText'

export default function InsuranceClaimsDashboard() {
  const router = useRouter()
  const { user, initializing } = useAuth(true)
  const { models, defaultModel, selectedModel, setSelectedModel } = useModel()
  const [claims, setClaims] = useState<any[]>([])
  const [policies, setPolicies] = useState<any[]>([])
  const [roles, setRoles] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  
  // Chatbot state
  const [chatOpen, setChatOpen] = useState(false)
  const [chatMessages, setChatMessages] = useState<{role: string, content: string}[]>([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const { isSupported: voiceSupported, isListening, toggle: toggleSpeechToText } = useSpeechToText({
    onTranscript: (text) => setChatInput(text),
  })

  useEffect(() => {
    if (user) {
      loadData()
    }
  }, [user])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  const loadData = async () => {
    try {
      const accessRes = await api.get<{roles: string[]}>('/api/apps/insurance-claims/access')
      setRoles(accessRes.roles)
      
      const claimsRes = await api.get<any[]>('/api/apps/insurance-claims/claims')
      setClaims(claimsRes)
      
      if (accessRes.roles.includes('customer')) {
        const policiesRes = await api.get<any[]>('/api/apps/insurance-claims/policies')
        setPolicies(policiesRes)
      }
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  const sendChatMessage = async () => {
    if (!chatInput.trim() || chatLoading) return
    
    const userMessage = chatInput.trim()
    setChatInput('')
    setChatMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setChatLoading(true)

    try {
      const context = `User has ${policies.length} policies and ${claims.length} claims. Roles: ${roles.join(', ')}.`
      
      const res = await api.post<{response: string}>('/api/apps/insurance-claims/chat', {
        message: userMessage,
        model: selectedModel,
        context
      })
      
      setChatMessages(prev => [...prev, { role: 'assistant', content: res.response }])
    } catch (error: any) {
      const errorMessage = error?.message || 'API call failed'
      setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ ${errorMessage}` }])
    } finally {
      setChatLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    const colors: any = {
      submitted: '#3b82f6', under_review: '#f59e0b', assigned: '#8b5cf6',
      investigating: '#06b6d4', approved: '#10b981', rejected: '#ef4444', settled: '#6366f1'
    }
    return colors[status] || '#64748b'
  }

  const getStatusIcon = (status: string) => {
    const icons: any = {
      submitted: '🔵', under_review: '🟡', assigned: '🟣',
      investigating: '🔍', approved: '✅', rejected: '❌', settled: '🟢'
    }
    return icons[status] || '📋'
  }

  if (initializing || loading) {
    return (
      <div style={{ minHeight: '100vh', background: '#0f172a', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div>Loading...</div>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a', color: 'white' }}>
      <header style={{ padding: '20px 40px', borderBottom: '1px solid #334155', background: '#1e293b' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ fontSize: '1.8rem', marginBottom: '8px' }}>🚗 Insurance Claims</h1>
            <div style={{ fontSize: '0.9rem', color: '#94a3b8' }}>
              Roles: {roles.map(r => r.charAt(0).toUpperCase() + r.slice(1)).join(', ')}
            </div>
          </div>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <ModelSelector value={selectedModel} onChange={setSelectedModel} models={models} defaultModel={defaultModel} />
            {roles.includes('customer') && (
              <>
                <button onClick={() => router.push('/apps/insurance-claims/buy-policy')}
                  style={{ padding: '10px 20px', background: '#06b6d4', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontWeight: '600' }}>
                  🛒 Buy Policy
                </button>
                <button onClick={() => router.push('/apps/insurance-claims/new-claim')}
                  style={{ padding: '10px 20px', background: '#10b981', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontWeight: '600' }}>
                  + File Claim
                </button>
              </>
            )}
            <button onClick={() => router.push('/')}
              style={{ padding: '10px 20px', background: '#334155', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer' }}>
              ← Back
            </button>
          </div>
        </div>
      </header>

      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '40px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: roles.includes('customer') ? '1fr 1fr' : '1fr', gap: '30px' }}>
          
          {roles.includes('customer') && (
            <div>
              <h2 style={{ fontSize: '1.5rem', marginBottom: '20px' }}>My Policies ({policies.length})</h2>
              {policies.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '60px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
                  <div style={{ fontSize: '3rem', marginBottom: '20px' }}>📋</div>
                  <p style={{ color: '#94a3b8', fontSize: '1.1rem', marginBottom: '20px' }}>No policies yet</p>
                  <button onClick={() => router.push('/apps/insurance-claims/buy-policy')}
                    style={{ padding: '12px 24px', background: '#06b6d4', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontWeight: '600' }}>
                    Buy Your First Policy
                  </button>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {policies.map((policy: any) => (
                    <div key={policy.id} style={{ background: '#1e293b', borderRadius: '12px', padding: '24px', border: '1px solid #334155' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '12px' }}>
                        <div>
                          <div style={{ fontSize: '1.1rem', fontWeight: 'bold', marginBottom: '4px' }}>📋 {policy.policy_number}</div>
                          <div style={{ fontSize: '0.9rem', color: '#94a3b8' }}>{policy.vehicle_make} {policy.vehicle_model} {policy.vehicle_year}</div>
                        </div>
                        <div style={{ padding: '4px 12px', background: policy.is_active ? '#10b98120' : '#64748b20', border: `1px solid ${policy.is_active ? '#10b981' : '#64748b'}`, borderRadius: '12px', fontSize: '0.75rem', fontWeight: '600', color: policy.is_active ? '#10b981' : '#64748b' }}>
                          {policy.is_active ? '✅ Active' : 'Inactive'}
                        </div>
                      </div>
                      <div style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '8px' }}>License: {policy.license_plate}</div>
                      <div style={{ fontSize: '0.9rem', color: '#10b981', fontWeight: '600' }}>Coverage: ${policy.coverage_amount.toLocaleString()}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div>
            <h2 style={{ fontSize: '1.5rem', marginBottom: '20px' }}>
              {roles.includes('customer') && 'My Claims'}
              {roles.includes('agent') && 'Claims to Review'}
              {roles.includes('adjuster') && 'Assigned Claims'}
              {roles.includes('manager') && 'Claims Management'}
              {' '}({claims.length})
            </h2>
            
            {claims.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '60px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
                <div style={{ fontSize: '3rem', marginBottom: '20px' }}>📋</div>
                <p style={{ color: '#94a3b8', fontSize: '1.1rem' }}>No claims found</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {claims.slice(0, 5).map((claim: any) => (
                  <div key={claim.id} onClick={() => router.push(`/apps/insurance-claims/claims/${claim.id}`)}
                    style={{ background: '#1e293b', borderRadius: '12px', padding: '20px', border: '1px solid #334155', cursor: 'pointer', transition: 'all 0.2s' }}
                    onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#6366f1'; e.currentTarget.style.transform = 'translateY(-2px)' }}
                    onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#334155'; e.currentTarget.style.transform = 'translateY(0)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '12px' }}>
                      <div>
                        <div style={{ fontSize: '1.1rem', fontWeight: 'bold', marginBottom: '4px' }}>{claim.claim_number}</div>
                        <div style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Filed: {new Date(claim.created_at).toLocaleDateString()}</div>
                      </div>
                      <div style={{ padding: '6px 14px', background: getStatusColor(claim.status), borderRadius: '12px', fontSize: '0.8rem', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {getStatusIcon(claim.status)} {claim.status.replace('_', ' ').toUpperCase()}
                      </div>
                    </div>
                    <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '8px', lineHeight: '1.5' }}>
                      {claim.incident_description.substring(0, 80)}...
                    </p>
                    {claim.approved_amount && (
                      <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid #334155', fontSize: '0.9rem', color: '#10b981', fontWeight: '600' }}>
                        Approved: ${claim.approved_amount.toLocaleString()}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Floating Chat Button */}
      <button onClick={() => setChatOpen(!chatOpen)}
        style={{ position: 'fixed', bottom: '24px', right: '24px', width: '60px', height: '60px', borderRadius: '50%', background: '#6366f1', border: 'none', color: 'white', fontSize: '1.5rem', cursor: 'pointer', boxShadow: '0 4px 12px rgba(99, 102, 241, 0.4)', zIndex: 1000 }}>
        {chatOpen ? '✕' : '💬'}
      </button>

      {/* Chat Modal */}
      {chatOpen && (
        <div style={{ position: 'fixed', bottom: '100px', right: '24px', width: '380px', height: '500px', background: '#1e293b', borderRadius: '16px', border: '1px solid #334155', display: 'flex', flexDirection: 'column', zIndex: 1000, boxShadow: '0 8px 32px rgba(0,0,0,0.3)' }}>
          <div style={{ padding: '16px', borderBottom: '1px solid #334155', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: '600', color: 'white' }}>🤖 Insurance Assistant</div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Ask about policies & claims</div>
            </div>
          </div>
          
          <div style={{ flex: 1, overflow: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {chatMessages.length === 0 && (
              <div style={{ textAlign: 'center', color: '#64748b', padding: '40px 20px' }}>
                <div style={{ fontSize: '2rem', marginBottom: '12px' }}>👋</div>
                <p>Hi! Ask me anything about insurance policies, claims, or coverage.</p>
              </div>
            )}
            {chatMessages.map((msg, i) => (
              <div key={i} style={{ alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '85%', padding: '10px 14px', borderRadius: '12px', background: msg.role === 'user' ? '#6366f1' : '#334155', color: 'white', fontSize: '0.9rem' }}>
                {msg.content}
              </div>
            ))}
            {chatLoading && (
              <div style={{ alignSelf: 'flex-start', padding: '10px 14px', borderRadius: '12px', background: '#334155', color: '#94a3b8' }}>
                Thinking...
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
          
	          <div style={{ padding: '12px', borderTop: '1px solid #334155', display: 'flex', gap: '8px' }}>
	            <input
	              value={chatInput}
	              onChange={(e) => setChatInput(e.target.value)}
	              onKeyPress={(e) => e.key === 'Enter' && sendChatMessage()}
	              placeholder="Ask a question..."
	              style={{ flex: 1, padding: '10px 14px', background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', color: 'white', outline: 'none' }}
	            />
	            <button
	              onClick={toggleSpeechToText}
	              disabled={!voiceSupported || chatLoading}
	              title={!voiceSupported ? 'Voice input not supported in this browser' : isListening ? 'Stop voice input' : 'Start voice input'}
	              style={{ padding: '10px 12px', background: isListening ? '#ef4444' : '#334155', border: 'none', borderRadius: '8px', color: 'white', cursor: !voiceSupported || chatLoading ? 'not-allowed' : 'pointer', opacity: !voiceSupported ? 0.5 : 1 }}
	            >
	              🎤
	            </button>
	            <button onClick={sendChatMessage} disabled={chatLoading}
	              style={{ padding: '10px 16px', background: '#6366f1', border: 'none', borderRadius: '8px', color: 'white', cursor: 'pointer' }}>
	              Send
	            </button>
	          </div>
        </div>
      )}
    </div>
  )
}
