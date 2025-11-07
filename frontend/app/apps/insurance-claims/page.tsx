'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function InsuranceClaimsDashboard() {
  const router = useRouter()
  const [claims, setClaims] = useState<any[]>([])
  const [policies, setPolicies] = useState<any[]>([])
  const [roles, setRoles] = useState<string[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/')
      return
    }
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const token = localStorage.getItem('token')
      
      const accessRes = await axios.get(`${API_URL}/api/apps/insurance-claims/access`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setRoles(accessRes.data.roles)
      
      const claimsRes = await axios.get(`${API_URL}/api/apps/insurance-claims/claims`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setClaims(claimsRes.data)
      
      if (accessRes.data.roles.includes('customer')) {
        const policiesRes = await axios.get(`${API_URL}/api/apps/insurance-claims/policies`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        setPolicies(policiesRes.data)
      }
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
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

  const getStatusIcon = (status: string) => {
    const icons: any = {
      submitted: '🔵',
      under_review: '🟡',
      assigned: '🟣',
      investigating: '🔍',
      approved: '✅',
      rejected: '❌',
      settled: '🟢'
    }
    return icons[status] || '📋'
  }

  if (loading) {
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
          <div style={{ display: 'flex', gap: '12px' }}>
            {roles.includes('customer') && (
              <>
                <button
                  onClick={() => router.push('/apps/insurance-claims/buy-policy')}
                  style={{ padding: '10px 20px', background: '#06b6d4', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontWeight: '600' }}
                >
                  🛒 Buy Policy
                </button>
                <button
                  onClick={() => router.push('/apps/insurance-claims/new-claim')}
                  style={{ padding: '10px 20px', background: '#10b981', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontWeight: '600' }}
                >
                  + File Claim
                </button>
              </>
            )}
            <button
              onClick={() => router.push('/')}
              style={{ padding: '10px 20px', background: '#334155', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer' }}
            >
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
                  <button
                    onClick={() => router.push('/apps/insurance-claims/buy-policy')}
                    style={{ padding: '12px 24px', background: '#06b6d4', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontWeight: '600' }}
                  >
                    Buy Your First Policy
                  </button>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {policies.map((policy: any) => (
                    <div
                      key={policy.id}
                      style={{
                        background: '#1e293b',
                        borderRadius: '12px',
                        padding: '24px',
                        border: '1px solid #334155'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '12px' }}>
                        <div>
                          <div style={{ fontSize: '1.1rem', fontWeight: 'bold', marginBottom: '4px' }}>
                            📋 {policy.policy_number}
                          </div>
                          <div style={{ fontSize: '0.9rem', color: '#94a3b8' }}>
                            {policy.vehicle_make} {policy.vehicle_model} {policy.vehicle_year}
                          </div>
                        </div>
                        <div
                          style={{
                            padding: '4px 12px',
                            background: policy.is_active ? '#10b98120' : '#64748b20',
                            border: `1px solid ${policy.is_active ? '#10b981' : '#64748b'}`,
                            borderRadius: '12px',
                            fontSize: '0.75rem',
                            fontWeight: '600',
                            color: policy.is_active ? '#10b981' : '#64748b'
                          }}
                        >
                          {policy.is_active ? '✅ Active' : 'Inactive'}
                        </div>
                      </div>
                      <div style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '8px' }}>
                        License: {policy.license_plate}
                      </div>
                      <div style={{ fontSize: '0.9rem', color: '#10b981', fontWeight: '600' }}>
                        Coverage: ${policy.coverage_amount.toLocaleString()}
                      </div>
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
                  <div
                    key={claim.id}
                    onClick={() => router.push(`/apps/insurance-claims/claims/${claim.id}`)}
                    style={{
                      background: '#1e293b',
                      borderRadius: '12px',
                      padding: '20px',
                      border: '1px solid #334155',
                      cursor: 'pointer',
                      transition: 'all 0.2s'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = '#6366f1'
                      e.currentTarget.style.transform = 'translateY(-2px)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = '#334155'
                      e.currentTarget.style.transform = 'translateY(0)'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '12px' }}>
                      <div>
                        <div style={{ fontSize: '1.1rem', fontWeight: 'bold', marginBottom: '4px' }}>
                          {claim.claim_number}
                        </div>
                        <div style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
                          Filed: {new Date(claim.created_at).toLocaleDateString()}
                        </div>
                      </div>
                      <div
                        style={{
                          padding: '6px 14px',
                          background: getStatusColor(claim.status),
                          borderRadius: '12px',
                          fontSize: '0.8rem',
                          fontWeight: '600',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}
                      >
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
                
                {claims.length > 5 && (
                  <button
                    onClick={() => router.push('/apps/insurance-claims/claims')}
                    style={{ padding: '12px', background: '#334155', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontWeight: '600' }}
                  >
                    View All {claims.length} Claims →
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
