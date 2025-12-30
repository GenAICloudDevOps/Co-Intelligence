'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import AppHeader from '../../../design-system/components/AppHeader'
import Card from '../../../design-system/components/Card'
import Button from '../../../design-system/components/Button'
import { api } from '../../../services/api'
import { useAuth } from '../../../hooks/useAuth'

export default function BuyPolicy() {
  const router = useRouter()
  const { initializing, user } = useAuth(true)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [formData, setFormData] = useState({
    vehicle_make: '',
    vehicle_model: '',
    vehicle_year: new Date().getFullYear(),
    license_plate: '',
    coverage_amount: 50000
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setMessage('')

    try {
      await api.post('/api/apps/insurance-claims/policies', formData)
      
      setMessage('Policy created successfully!')
      setTimeout(() => {
        router.push('/apps/insurance-claims')
      }, 1500)
    } catch (error: any) {
      setMessage('Failed to create policy')
    } finally {
      setLoading(false)
    }
  }

  if (initializing || !user) {
    return (
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0a0f1e 0%, #1a1042 100%)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div>Loading...</div>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0a0f1e 0%, #1a1042 100%)', color: 'white' }}>
      <AppHeader appName="Buy Insurance Policy" />

      <div style={{ maxWidth: '800px', margin: '0 auto', padding: '40px' }}>
        <Card padding="lg">
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#c7d2fe' }}>
                Vehicle Make *
              </label>
              <input
                type="text"
                value={formData.vehicle_make}
                onChange={(e) => setFormData({ ...formData, vehicle_make: e.target.value })}
                placeholder="e.g., Toyota, Honda, Ford"
                required
                style={{ width: '100%', padding: '12px', background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(139, 92, 246, 0.3)', borderRadius: '10px', color: 'white', outline: 'none' }}
              />
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#c7d2fe' }}>
                Vehicle Model *
              </label>
              <input
                type="text"
                value={formData.vehicle_model}
                onChange={(e) => setFormData({ ...formData, vehicle_model: e.target.value })}
                placeholder="e.g., Camry, Accord, F-150"
                required
                style={{ width: '100%', padding: '12px', background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(139, 92, 246, 0.3)', borderRadius: '10px', color: 'white', outline: 'none' }}
              />
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#c7d2fe' }}>
                Vehicle Year *
              </label>
              <input
                type="number"
                value={formData.vehicle_year}
                onChange={(e) => setFormData({ ...formData, vehicle_year: parseInt(e.target.value) })}
                min="1990"
                max={new Date().getFullYear() + 1}
                required
                style={{ width: '100%', padding: '12px', background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(139, 92, 246, 0.3)', borderRadius: '10px', color: 'white', outline: 'none' }}
              />
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#c7d2fe' }}>
                License Plate *
              </label>
              <input
                type="text"
                value={formData.license_plate}
                onChange={(e) => setFormData({ ...formData, license_plate: e.target.value.toUpperCase() })}
                placeholder="e.g., ABC1234"
                required
                style={{ width: '100%', padding: '12px', background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(139, 92, 246, 0.3)', borderRadius: '10px', color: 'white', outline: 'none', textTransform: 'uppercase' }}
              />
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#c7d2fe' }}>
                Coverage Amount *
              </label>
              <select
                value={formData.coverage_amount}
                onChange={(e) => setFormData({ ...formData, coverage_amount: parseFloat(e.target.value) })}
                required
                style={{ width: '100%', padding: '12px', background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(139, 92, 246, 0.3)', borderRadius: '10px', color: 'white', outline: 'none' }}
              >
                <option value="25000">$25,000</option>
                <option value="50000">$50,000</option>
                <option value="100000">$100,000</option>
                <option value="250000">$250,000</option>
              </select>
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
                {loading ? 'Creating Policy...' : 'Buy Policy'}
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
    </div>
  )
}
