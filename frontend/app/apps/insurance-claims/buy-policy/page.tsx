'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function BuyPolicy() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [formData, setFormData] = useState({
    vehicle_make: '',
    vehicle_model: '',
    vehicle_year: new Date().getFullYear(),
    license_plate: '',
    coverage_amount: 50000
  })

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/')
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setMessage('')

    try {
      const token = localStorage.getItem('token')
      await axios.post(`${API_URL}/api/apps/insurance-claims/policies`, formData, {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      setMessage('Policy created successfully!')
      setTimeout(() => {
        router.push('/apps/insurance-claims')
      }, 1500)
    } catch (error: any) {
      setMessage(error.response?.data?.detail || 'Failed to create policy')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a', color: 'white' }}>
      <header style={{ padding: '20px 40px', borderBottom: '1px solid #334155', background: '#1e293b' }}>
        <h1 style={{ fontSize: '1.8rem' }}>🚗 Buy Insurance Policy</h1>
      </header>

      <div style={{ maxWidth: '800px', margin: '0 auto', padding: '40px' }}>
        <div style={{ background: '#1e293b', borderRadius: '12px', padding: '40px', border: '1px solid #334155' }}>
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#94a3b8' }}>
                Vehicle Make *
              </label>
              <input
                type="text"
                value={formData.vehicle_make}
                onChange={(e) => setFormData({ ...formData, vehicle_make: e.target.value })}
                placeholder="e.g., Toyota, Honda, Ford"
                required
                style={{ width: '100%', padding: '12px', background: '#0f172a', border: '1px solid #334155', borderRadius: '6px', color: 'white' }}
              />
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#94a3b8' }}>
                Vehicle Model *
              </label>
              <input
                type="text"
                value={formData.vehicle_model}
                onChange={(e) => setFormData({ ...formData, vehicle_model: e.target.value })}
                placeholder="e.g., Camry, Accord, F-150"
                required
                style={{ width: '100%', padding: '12px', background: '#0f172a', border: '1px solid #334155', borderRadius: '6px', color: 'white' }}
              />
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#94a3b8' }}>
                Vehicle Year *
              </label>
              <input
                type="number"
                value={formData.vehicle_year}
                onChange={(e) => setFormData({ ...formData, vehicle_year: parseInt(e.target.value) })}
                min="1990"
                max={new Date().getFullYear() + 1}
                required
                style={{ width: '100%', padding: '12px', background: '#0f172a', border: '1px solid #334155', borderRadius: '6px', color: 'white' }}
              />
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#94a3b8' }}>
                License Plate *
              </label>
              <input
                type="text"
                value={formData.license_plate}
                onChange={(e) => setFormData({ ...formData, license_plate: e.target.value.toUpperCase() })}
                placeholder="e.g., ABC1234"
                required
                style={{ width: '100%', padding: '12px', background: '#0f172a', border: '1px solid #334155', borderRadius: '6px', color: 'white', textTransform: 'uppercase' }}
              />
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#94a3b8' }}>
                Coverage Amount *
              </label>
              <select
                value={formData.coverage_amount}
                onChange={(e) => setFormData({ ...formData, coverage_amount: parseFloat(e.target.value) })}
                required
                style={{ width: '100%', padding: '12px', background: '#0f172a', border: '1px solid #334155', borderRadius: '6px', color: 'white' }}
              >
                <option value="25000">$25,000</option>
                <option value="50000">$50,000</option>
                <option value="100000">$100,000</option>
                <option value="250000">$250,000</option>
              </select>
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
                style={{ flex: 1, padding: '14px', background: loading ? '#475569' : '#06b6d4', border: 'none', borderRadius: '6px', color: 'white', fontSize: '1rem', cursor: loading ? 'not-allowed' : 'pointer', fontWeight: '600' }}
              >
                {loading ? 'Creating Policy...' : 'Buy Policy'}
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
