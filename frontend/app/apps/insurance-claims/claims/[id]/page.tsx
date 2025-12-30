'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import AppHeader from '../../../../design-system/components/AppHeader'
import Card from '../../../../design-system/components/Card'
import Button from '../../../../design-system/components/Button'
import { api } from '../../../../services/api'
import { useAuth } from '../../../../hooks/useAuth'

export default function ClaimDetail() {
  const router = useRouter()
  const params = useParams()
  const { user, initializing } = useAuth(true)
  const [claim, setClaim] = useState<any>(null)
  const [roles, setRoles] = useState<string[]>([])
  const [adjusters, setAdjusters] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const [newStatus, setNewStatus] = useState('')
  const [assignedAdjusterId, setAssignedAdjusterId] = useState('')
  const [approvedAmount, setApprovedAmount] = useState('')

  useEffect(() => {
    if (user) {
      loadData()
    }
  }, [user, params.id])

  const loadData = async () => {
    try {
      const accessRes = await api.get<{roles: string[]}>('/api/apps/insurance-claims/access')
      setRoles(accessRes.roles)
      
      const claimRes = await api.get<any>(`/api/apps/insurance-claims/claims/${params.id}`)
      setClaim(claimRes)
      setNewStatus(claimRes.status)
      
      if (accessRes.roles.includes('manager')) {
        const adjustersRes = await api.get<any[]>('/api/apps/insurance-claims/adjusters')
        setAdjusters(adjustersRes)
      }
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateStatus = async () => {
    setUpdating(true)
    try {
      await api.put(`/api/apps/insurance-claims/claims/${params.id}/status`, {
        status: newStatus,
        assigned_adjuster_id: assignedAdjusterId ? parseInt(assignedAdjusterId) : null,
        approved_amount: approvedAmount ? parseFloat(approvedAmount) : null
      })
      await loadData()
      alert('Status updated successfully!')
    } catch (error: any) {
      alert('Failed to update status')
    } finally {
      setUpdating(false)
    }
  }

  const getStatusColor = (status: string) => {
    const colors: any = {
      submitted: '#3b82f6',
      under_review: '#f59e0b',
      assigned: '#8b5cf6',
      investigating: '#06b6d4',
      approved: '#10b981',
      rejected: '#ef4444',
      settled: '#6366f1'
    }
    return colors[status] || '#64748b'
  }

  const getAvailableStatuses = () => {
    if (!claim) return []
    
    const transitions: any = {
      submitted: roles.includes('agent') || roles.includes('manager') ? ['under_review', 'rejected'] : [],
      under_review: roles.includes('manager') ? ['assigned', 'rejected'] : [],
      assigned: roles.includes('adjuster') || roles.includes('manager') ? ['investigating', 'rejected'] : [],
      investigating: roles.includes('adjuster') ? ['approved', 'rejected'] : [],
      approved: roles.includes('manager') ? ['settled'] : [],
      rejected: [],
      settled: []
    }
    
    return transitions[claim.status] || []
  }

  if (initializing || loading) {
    return (
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0a0f1e 0%, #1a1042 100%)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div>Loading...</div>
      </div>
    )
  }

  if (!claim) {
    return (
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0a0f1e 0%, #1a1042 100%)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div>Claim not found</div>
      </div>
    )
  }

  const availableStatuses = getAvailableStatuses()

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0a0f1e 0%, #1a1042 100%)', color: 'white' }}>
      <AppHeader appName="Claim Details" />

      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '40px' }}>
        <div style={{ marginBottom: '24px' }}>
          <Button variant="secondary" size="sm" onClick={() => router.push('/apps/insurance-claims')}>
            ← Back to Dashboard
          </Button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
          {/* Main Info */}
          <Card padding="lg">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '24px' }}>
              <div>
                <h2 style={{ fontSize: '1.5rem', marginBottom: '8px', color: 'white' }}>{claim.claim_number}</h2>
                <div style={{ fontSize: '0.9rem', color: '#c7d2fe' }}>
                  Filed: {new Date(claim.created_at).toLocaleDateString()}
                </div>
              </div>
              <div
                style={{
                  padding: '8px 16px',
                  background: getStatusColor(claim.status),
                  borderRadius: '12px',
                  fontSize: '0.85rem',
                  fontWeight: '600',
                  color: 'white'
                }}
              >
                {claim.status.replace('_', ' ').toUpperCase()}
              </div>
            </div>

            <div style={{ marginBottom: '24px' }}>
              <h3 style={{ fontSize: '1.1rem', marginBottom: '12px', color: '#c7d2fe' }}>Incident Details</h3>
              <div style={{ marginBottom: '12px', color: 'white' }}>
                <strong>Date:</strong> {new Date(claim.incident_date).toLocaleString()}
              </div>
              <div style={{ marginBottom: '12px', color: 'white' }}>
                <strong>Location:</strong> {claim.incident_location}
              </div>
              <div style={{ color: 'white' }}>
                <strong>Description:</strong>
                <p style={{ marginTop: '8px', color: '#c7d2fe', lineHeight: '1.6' }}>
                  {claim.incident_description}
                </p>
              </div>
            </div>

            {claim.estimated_damage && (
              <div style={{ marginBottom: '12px', padding: '12px', background: 'rgba(15, 23, 42, 0.8)', borderRadius: '10px', color: 'white' }}>
                <strong>Estimated Damage:</strong> ${claim.estimated_damage.toLocaleString()}
              </div>
            )}

            {claim.approved_amount && (
              <div style={{ padding: '12px', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid #10b981', borderRadius: '10px', color: '#10b981' }}>
                <strong>Approved Amount:</strong> ${claim.approved_amount.toLocaleString()}
              </div>
            )}
          </Card>

          {/* Actions Panel */}
          <Card padding="lg">
            <h3 style={{ fontSize: '1.2rem', marginBottom: '20px', color: 'white' }}>Actions</h3>

            {availableStatuses.length > 0 && (
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#c7d2fe' }}>
                  Update Status
                </label>
                <select
                  value={newStatus}
                  onChange={(e) => setNewStatus(e.target.value)}
                  style={{ width: '100%', padding: '10px', background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(139, 92, 246, 0.3)', borderRadius: '10px', color: 'white', marginBottom: '12px', outline: 'none' }}
                >
                  <option value={claim.status}>{claim.status.replace('_', ' ')}</option>
                  {availableStatuses.map((status: string) => (
                    <option key={status} value={status}>
                      {status.replace('_', ' ')}
                    </option>
                  ))}
                </select>

                {newStatus === 'assigned' && roles.includes('manager') && (
                  <select
                    value={assignedAdjusterId}
                    onChange={(e) => setAssignedAdjusterId(e.target.value)}
                    style={{ width: '100%', padding: '10px', background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(139, 92, 246, 0.3)', borderRadius: '10px', color: 'white', marginBottom: '12px', outline: 'none' }}
                  >
                    <option value="">Select Adjuster</option>
                    {adjusters.map((adj) => (
                      <option key={adj.id} value={adj.id}>{adj.name}</option>
                    ))}
                  </select>
                )}

                {newStatus === 'approved' && roles.includes('adjuster') && (
                  <input
                    type="number"
                    placeholder="Approved Amount"
                    value={approvedAmount}
                    onChange={(e) => setApprovedAmount(e.target.value)}
                    style={{ width: '100%', padding: '10px', background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(139, 92, 246, 0.3)', borderRadius: '10px', color: 'white', marginBottom: '12px', outline: 'none' }}
                  />
                )}

                <Button
                  variant="primary"
                  onClick={handleUpdateStatus}
                  disabled={updating || newStatus === claim.status}
                  style={{ width: '100%' }}
                >
                  {updating ? 'Updating...' : 'Update Status'}
                </Button>
              </div>
            )}

            {availableStatuses.length === 0 && (
              <div style={{ padding: '16px', background: 'rgba(15, 23, 42, 0.8)', borderRadius: '10px', color: '#c7d2fe', textAlign: 'center' }}>
                No actions available
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
