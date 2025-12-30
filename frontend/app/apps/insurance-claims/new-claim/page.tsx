'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import AppHeader from '../../../design-system/components/AppHeader'
import Card from '../../../design-system/components/Card'
import Button from '../../../design-system/components/Button'
import Modal from '../../../design-system/components/Modal'
import { api } from '../../../services/api'
import { useAuth } from '../../../hooks/useAuth'
import { useModel } from '../../../components/ModelProvider'

export default function NewClaim() {
  const router = useRouter()
  const { user, initializing } = useAuth(true)
  const { selectedModel } = useModel()
  const [policies, setPolicies] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [checkingPolicies, setCheckingPolicies] = useState(true)
  const [message, setMessage] = useState('')
  const [formData, setFormData] = useState({
    policy_id: '',
    incident_date: '',
    incident_description: '',
    incident_location: ''
  })
  const [rewriteModal, setRewriteModal] = useState<{ show: boolean; field: string; original: string; rewritten: string; loading: boolean }>({
    show: false,
    field: '',
    original: '',
    rewritten: '',
    loading: false
  })

  useEffect(() => {
    if (user) {
      loadPolicies()
    }
  }, [user])

  const handleRewrite = async (field: 'incident_location' | 'incident_description') => {
    const text = formData[field]
    if (!text.trim()) {
      setMessage('Please enter text before rewriting')
      return
    }

    setRewriteModal({ show: true, field, original: text, rewritten: '', loading: true })

    try {
      const res = await api.post<{rewritten_text: string}>('/api/apps/insurance-claims/rewrite', {
        text,
        model: selectedModel
      })
      setRewriteModal(prev => ({ ...prev, rewritten: res.rewritten_text, loading: false }))
    } catch (error) {
      console.error('Error rewriting:', error)
      setRewriteModal(prev => ({ ...prev, loading: false }))
      setMessage('Failed to rewrite text')
    }
  }

  const acceptRewrite = () => {
    setFormData(prev => ({ ...prev, [rewriteModal.field]: rewriteModal.rewritten }))
    setRewriteModal({ show: false, field: '', original: '', rewritten: '', loading: false })
  }

  const rejectRewrite = () => {
    setRewriteModal({ show: false, field: '', original: '', rewritten: '', loading: false })
  }

  const loadPolicies = async () => {
    try {
      const res = await api.get<any[]>('/api/apps/insurance-claims/policies')
      setPolicies(res)
      if (res.length > 0) {
        setFormData(prev => ({ ...prev, policy_id: res[0].id.toString() }))
      }
    } catch (error) {
      console.error('Error loading policies:', error)
    } finally {
      setCheckingPolicies(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setMessage('')

    try {
      await api.post('/api/apps/insurance-claims/claims', {
        ...formData,
        policy_id: parseInt(formData.policy_id),
        incident_date: new Date(formData.incident_date).toISOString()
      })
      
      setMessage('Claim submitted successfully!')
      setTimeout(() => {
        router.push('/apps/insurance-claims')
      }, 1500)
    } catch (error: any) {
      setMessage('Failed to submit claim')
    } finally {
      setLoading(false)
    }
  }

  if (initializing || checkingPolicies) {
    return (
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0a0f1e 0%, #1a1042 100%)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div>Loading...</div>
      </div>
    )
  }

  if (policies.length === 0) {
    return (
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0a0f1e 0%, #1a1042 100%)', color: 'white' }}>
        <AppHeader appName="File New Claim" />

        <div style={{ maxWidth: '800px', margin: '0 auto', padding: '40px' }}>
          <Card padding="lg">
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <div style={{ fontSize: '4rem', marginBottom: '20px' }}>🚗</div>
              <h2 style={{ fontSize: '1.5rem', marginBottom: '16px', color: 'white' }}>No Insurance Policy Found</h2>
              <p style={{ color: '#c7d2fe', fontSize: '1.1rem', marginBottom: '30px', lineHeight: '1.6' }}>
                You need to purchase an insurance policy before filing a claim.
              </p>
              <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
                <Button variant="primary" onClick={() => router.push('/apps/insurance-claims/buy-policy')}>
                  🛒 Buy Policy
                </Button>
                <Button variant="secondary" onClick={() => router.push('/apps/insurance-claims')}>
                  ← Back to Dashboard
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0a0f1e 0%, #1a1042 100%)', color: 'white' }}>
      <AppHeader appName="File New Claim" />

      <div style={{ maxWidth: '800px', margin: '0 auto', padding: '40px' }}>
        <Card padding="lg">
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#c7d2fe' }}>
                Select Policy *
              </label>
              <select
                value={formData.policy_id}
                onChange={(e) => setFormData({ ...formData, policy_id: e.target.value })}
                required
                style={{ width: '100%', padding: '12px', background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(139, 92, 246, 0.3)', borderRadius: '10px', color: 'white', outline: 'none' }}
              >
                {policies.map((policy) => (
                  <option key={policy.id} value={policy.id}>
                    {policy.policy_number} - {policy.vehicle_make} {policy.vehicle_model} {policy.vehicle_year}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#c7d2fe' }}>
                Incident Date *
              </label>
              <input
                type="datetime-local"
                value={formData.incident_date}
                onChange={(e) => setFormData({ ...formData, incident_date: e.target.value })}
                required
                style={{ width: '100%', padding: '12px', background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(139, 92, 246, 0.3)', borderRadius: '10px', color: 'white', outline: 'none' }}
              />
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#c7d2fe' }}>
                Incident Location *
              </label>
              <input
                type="text"
                value={formData.incident_location}
                onChange={(e) => setFormData({ ...formData, incident_location: e.target.value })}
                placeholder="e.g., Main St & 5th Ave, Seattle, WA"
                required
                style={{ width: '100%', padding: '12px', background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(139, 92, 246, 0.3)', borderRadius: '10px', color: 'white', outline: 'none' }}
              />
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#c7d2fe' }}>
                Incident Description *
              </label>
              <textarea
                value={formData.incident_description}
                onChange={(e) => setFormData({ ...formData, incident_description: e.target.value })}
                placeholder="Describe what happened..."
                required
                rows={6}
                style={{ width: '100%', padding: '12px', background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(139, 92, 246, 0.3)', borderRadius: '10px', color: 'white', outline: 'none', resize: 'vertical' }}
              />
              <Button
                type="button"
                variant="primary"
                size="sm"
                onClick={() => handleRewrite('incident_description')}
                style={{ marginTop: '8px' }}
              >
                ✨ Rewrite with AI
              </Button>
            </div>

            {message && (
              <div style={{ marginBottom: '20px', padding: '12px', background: message.includes('success') ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)', border: `1px solid ${message.includes('success') ? '#10b981' : '#ef4444'}`, borderRadius: '10px', color: message.includes('success') ? '#10b981' : '#ef4444' }}>
                {message}
              </div>
            )}

            <div style={{ display: 'flex', gap: '12px' }}>
              <Button
                type="submit"
                variant="primary"
                disabled={loading}
                style={{ flex: 1 }}
              >
                {loading ? 'Submitting...' : 'Submit Claim'}
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => router.push('/apps/insurance-claims')}
              >
                Cancel
              </Button>
            </div>
          </form>
        </Card>
      </div>

      <Modal
        isOpen={rewriteModal.show}
        onClose={rejectRewrite}
        title="✨ AI Rewrite Suggestion"
      >
        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#c7d2fe' }}>Original:</label>
          <div style={{ padding: '12px', background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(139, 92, 246, 0.2)', borderRadius: '10px', color: '#94a3b8' }}>
            {rewriteModal.original}
          </div>
        </div>

        {rewriteModal.loading ? (
          <div style={{ padding: '24px', textAlign: 'center', color: '#c7d2fe' }}>
            <div style={{ marginBottom: '12px' }}>🤖 AI is rewriting...</div>
          </div>
        ) : (
          <>
            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#c7d2fe' }}>AI Suggestion:</label>
              <div style={{ padding: '12px', background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(139, 92, 246, 0.5)', borderRadius: '10px', color: 'white' }}>
                {rewriteModal.rewritten}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <Button variant="secondary" onClick={rejectRewrite}>
                ❌ Reject
              </Button>
              <Button variant="primary" onClick={acceptRewrite}>
                ✅ Accept
              </Button>
            </div>
          </>
        )}
      </Modal>
    </div>
  )
}
