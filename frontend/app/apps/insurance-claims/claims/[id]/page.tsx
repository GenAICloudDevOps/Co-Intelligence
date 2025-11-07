'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function ClaimDetail() {
  const router = useRouter()
  const params = useParams()
  const [claim, setClaim] = useState<any>(null)
  const [roles, setRoles] = useState<string[]>([])
  const [adjusters, setAdjusters] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const [newStatus, setNewStatus] = useState('')
  const [assignedAdjusterId, setAssignedAdjusterId] = useState('')
  const [approvedAmount, setApprovedAmount] = useState('')

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/')
      return
    }
    loadData()
  }, [params.id])

  const loadData = async () => {
    try {
      const token = localStorage.getItem('token')
      
      // Get roles
      const accessRes = await axios.get(`${API_URL}/api/apps/insurance-claims/access`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setRoles(accessRes.data.roles)
      
      // Get claim
      const claimRes = await axios.get(`${API_URL}/api/apps/insurance-claims/claims/${params.id}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setClaim(claimRes.data)
      setNewStatus(claimRes.data.status)
      
      // Get adjusters if manager
      if (accessRes.data.roles.includes('manager')) {
        const adjustersRes = await axios.get(`${API_URL}/api/apps/insurance-claims/adjusters`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        setAdjusters(adjustersRes.data)
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
      const token = localStorage.getItem('token')
      await axios.put(`${API_URL}/api/apps/insurance-claims/claims/${params.id}/status`, {
        status: newStatus,
        assigned_adjuster_id: assignedAdjusterId ? parseInt(assignedAdjusterId) : null,
        approved_amount: approvedAmount ? parseFloat(approvedAmount) : null
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      await loadData()
      alert('Status updated successfully!')
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to update status')
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

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', background: '#0f172a', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div>Loading...</div>
      </div>
    )
  }

  if (!claim) {
    return (
      <div style={{ minHeight: '100vh', background: '#0f172a', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div>Claim not found</div>
      </div>
    )
  }

  const availableStatuses = getAvailableStatuses()

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a', color: 'white' }}>
      <header style={{ padding: '20px 40px', borderBottom: '1px solid #334155', background: '#1e293b' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1 style={{ fontSize: '1.8rem' }}>Claim Details</h1>
          <button
            onClick={() => router.push('/apps/insurance-claims')}
            style={{ padding: '10px 20px', background: '#334155', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer' }}
          >
            ← Back
          </button>
        </div>
      </header>

      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '40px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
          {/* Main Info */}
          <div style={{ background: '#1e293b', borderRadius: '12px', padding: '32px', border: '1px solid #334155' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '24px' }}>
              <div>
                <h2 style={{ fontSize: '1.5rem', marginBottom: '8px' }}>{claim.claim_number}</h2>
                <div style={{ fontSize: '0.9rem', color: '#94a3b8' }}>
                  Filed: {new Date(claim.created_at).toLocaleDateString()}
                </div>
              </div>
              <div
                style={{
                  padding: '8px 16px',
                  background: getStatusColor(claim.status),
                  borderRadius: '12px',
                  fontSize: '0.85rem',
                  fontWeight: '600'
                }}
              >
                {claim.status.replace('_', ' ').toUpperCase()}
              </div>
            </div>

            <div style={{ marginBottom: '24px' }}>
              <h3 style={{ fontSize: '1.1rem', marginBottom: '12px', color: '#94a3b8' }}>Incident Details</h3>
              <div style={{ marginBottom: '12px' }}>
                <strong>Date:</strong> {new Date(claim.incident_date).toLocaleString()}
              </div>
              <div style={{ marginBottom: '12px' }}>
                <strong>Location:</strong> {claim.incident_location}
              </div>
              <div>
                <strong>Description:</strong>
                <p style={{ marginTop: '8px', color: '#94a3b8', lineHeight: '1.6' }}>
                  {claim.incident_description}
                </p>
              </div>
            </div>

            {claim.estimated_damage && (
              <div style={{ marginBottom: '12px', padding: '12px', background: '#0f172a', borderRadius: '6px' }}>
                <strong>Estimated Damage:</strong> ${claim.estimated_damage.toLocaleString()}
              </div>
            )}

            {claim.approved_amount && (
              <div style={{ padding: '12px', background: '#10b98120', border: '1px solid #10b981', borderRadius: '6px', color: '#10b981' }}>
                <strong>Approved Amount:</strong> ${claim.approved_amount.toLocaleString()}
              </div>
            )}
          </div>

          {/* Actions Panel */}
          <div style={{ background: '#1e293b', borderRadius: '12px', padding: '32px', border: '1px solid #334155' }}>
            <h3 style={{ fontSize: '1.2rem', marginBottom: '20px' }}>Actions</h3>

            {availableStatuses.length > 0 && (
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: '#94a3b8' }}>
                  Update Status
                </label>
                <select
                  value={newStatus}
                  onChange={(e) => setNewStatus(e.target.value)}
                  style={{ width: '100%', padding: '10px', background: '#0f172a', border: '1px solid #334155', borderRadius: '6px', color: 'white', marginBottom: '12px' }}
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
                    style={{ width: '100%', padding: '10px', background: '#0f172a', border: '1px solid #334155', borderRadius: '6px', color: 'white', marginBottom: '12px' }}
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
                    style={{ width: '100%', padding: '10px', background: '#0f172a', border: '1px solid #334155', borderRadius: '6px', color: 'white', marginBottom: '12px' }}
                  />
                )}

                <button
                  onClick={handleUpdateStatus}
                  disabled={updating || newStatus === claim.status}
                  style={{ width: '100%', padding: '12px', background: updating || newStatus === claim.status ? '#475569' : '#6366f1', border: 'none', borderRadius: '6px', color: 'white', cursor: updating || newStatus === claim.status ? 'not-allowed' : 'pointer', fontWeight: '600' }}
                >
                  {updating ? 'Updating...' : 'Update Status'}
                </button>
              </div>
            )}

            {availableStatuses.length === 0 && (
              <div style={{ padding: '16px', background: '#0f172a', borderRadius: '6px', color: '#94a3b8', textAlign: 'center' }}>
                No actions available
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
