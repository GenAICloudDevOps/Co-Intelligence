'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function NewClaim() {
  const router = useRouter()
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

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/')
      return
    }
    loadPolicies()
  }, [])

  const loadPolicies = async () => {
    try {
      const token = localStorage.getItem('token')
      const res = await axios.get(`${API_URL}/api/apps/insurance-claims/policies`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setPolicies(res.data)
      if (res.data.length > 0) {
        setFormData(prev => ({ ...prev, policy_id: res.data[0].id.toString() }))
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
      const token = localStorage.getItem('token')
      await axios.post(`${API_URL}/api/apps/insurance-claims/claims`, {
        ...formData,
        policy_id: parseInt(formData.policy_id),
        incident_date: new Date(formData.incident_date).toISOString()
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      setMessage('Claim submitted successfully!')
      setTimeout(() => {
        router.push('/apps/insurance-claims')
      }, 1500)
    } catch (error: any) {
      setMessage(error.response?.data?.detail || 'Failed to submit claim')
    } finally {
      setLoading(false)
    }
  }

  if (checkingPolicies) {
    return (
      <div style={{ minHeight: '100vh', background: '#0f172a', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div>Loading...</div>
      </div>
    )
  }

  if (policies.length === 0) {
    return (
      <div style={{ minHeight: '100vh', background: '#0f172a', color: 'white' }}>
        <header style={{ padding: '20px 40px', borderBottom: '1px solid #334155', background: '#1e293b' }}>
          <h1 style={{ fontSize: '1.8rem' }}>📝 File New Claim</h1>
        </header>

        <div style={{ maxWidth: '800px', margin: '0 auto', padding: '40px' }}>
          <div style={{ textAlign: 'center', padding: '60px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
            <div style={{ fontSize: '4rem', marginBottom: '20px' }}>🚗</div>
            <h2 style={{ fontSize: '1.5rem', marginBottom: '16px' }}>No Insurance Policy Found</h2>
            <p style={{ color: '#94a3b8', fontSize: '1.1rem', marginBottom: '30px', lineHeight: '1.6' }}>
              You need to purchase an insurance policy before filing a claim.
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button
                onClick={() => router.push('/apps/insurance-claims/buy-policy')}
                style={{ padding: '14px 28px', background: '#06b6d4', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontWeight: '600', fontSize: '1rem' }}
              >
                🛒 Buy Policy
              </button>
              <button
                onClick={() => router.push('/apps/insurance-claims')}
                style={{ padding: '14px 28px', background: '#334155', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontSize: '1rem' }}
              >
                ← Back to Dashboard
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a', color: 'white' }}>
      <header style={{ padding: '20px 40px', borderBottom: '1px solid #334155', background: '#1e293b' }}>
        <h1 style={{ fontSize: '1.8rem' }}>📝 File New Claim</h1>
      </header>

      <div style={{ maxWidth: '800px', margin: '0 auto', padding: '40px' }}>
        <div style={{ background: '#1e293b', borderRadius: '12px', padding: '40px', border: '1px solid #334155' }}>
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#94a3b8' }}>
                Select Policy *
              </label>
              <select
                value={formData.policy_id}
                onChange={(e) => setFormData({ ...formData, policy_id: e.target.value })}
                required
                style={{ width: '100%', padding: '12px', background: '#0f172a', border: '1px solid #334155', borderRadius: '6px', color: 'white' }}
              >
                {policies.map((policy) => (
                  <option key={policy.id} value={policy.id}>
                    {policy.policy_number} - {policy.vehicle_make} {policy.vehicle_model} {policy.vehicle_year}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#94a3b8' }}>
                Incident Date *
              </label>
              <input
                type="datetime-local"
                value={formData.incident_date}
                onChange={(e) => setFormData({ ...formData, incident_date: e.target.value })}
                required
                style={{ width: '100%', padding: '12px', background: '#0f172a', border: '1px solid #334155', borderRadius: '6px', color: 'white' }}
              />
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#94a3b8' }}>
                Incident Location *
              </label>
              <input
                type="text"
                value={formData.incident_location}
                onChange={(e) => setFormData({ ...formData, incident_location: e.target.value })}
                placeholder="e.g., Main St & 5th Ave, Seattle, WA"
                required
                style={{ width: '100%', padding: '12px', background: '#0f172a', border: '1px solid #334155', borderRadius: '6px', color: 'white' }}
              />
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#94a3b8' }}>
                Incident Description *
              </label>
              <textarea
                value={formData.incident_description}
                onChange={(e) => setFormData({ ...formData, incident_description: e.target.value })}
                placeholder="Describe what happened..."
                required
                rows={6}
                style={{ width: '100%', padding: '12px', background: '#0f172a', border: '1px solid #334155', borderRadius: '6px', color: 'white', resize: 'vertical' }}
              />
            </div>

            {message && (
              <div style={{ marginBottom: '20px', padding: '12px', background: message.includes('success') ? '#10b98120' : '#ef444420', border: `1px solid ${message.includes('success') ? '#10b981' : '#ef4444'}`, borderRadius: '6px', color: message.includes('success') ? '#10b981' : '#ef4444' }}>
                {message}
              </div>
            )}

            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                type="submit"
                disabled={loading}
                style={{ flex: 1, padding: '14px', background: loading ? '#475569' : '#10b981', border: 'none', borderRadius: '6px', color: 'white', fontSize: '1rem', cursor: loading ? 'not-allowed' : 'pointer', fontWeight: '600' }}
              >
                {loading ? 'Submitting...' : 'Submit Claim'}
              </button>
              <button
                type="button"
                onClick={() => router.push('/apps/insurance-claims')}
                style={{ padding: '14px 24px', background: '#334155', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer' }}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
