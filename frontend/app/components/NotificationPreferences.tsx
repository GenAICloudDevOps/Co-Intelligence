'use client'

import React, { useState, useEffect } from 'react'
import { api } from '../services/api'

interface NotificationPreferences {
    global_email_enabled: boolean
    apps: string[]
    preferences: Record<string, { email_enabled: boolean; in_app_enabled: boolean }>
}

interface NotificationPreferencesProps {
    theme: {
        panelBg: string
        panelAltBg: string
        border: string
        mutedText: string
        softText: string
        accent: string
        success: string
        controlBg: string
    }
    onGlobalEmailToggle: () => void
    globalEmailEnabled: boolean
}

const APP_LABELS: Record<string, { icon: string; name: string }> = {
    'agentic-barista': { icon: '☕', name: 'Agentic Barista' },
    'agentic-lms': { icon: '🎓', name: 'Agentic LMS' },
    'insurance-claims': { icon: '🚗', name: 'Insurance Claims' },
    'llms-fine-tuning': { icon: '🧪', name: 'LLMs Fine-Tuning' },
    'data-analysis': { icon: '📊', name: 'Data Analysis' },
}

export default function NotificationPreferences({ theme, onGlobalEmailToggle, globalEmailEnabled }: NotificationPreferencesProps) {
    const [prefs, setPrefs] = useState<NotificationPreferences | null>(null)
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [expanded, setExpanded] = useState(false)

    const fetchPrefs = async () => {
        try {
            const data = await api.get<NotificationPreferences>('/api/auth/notifications/preferences')
            setPrefs(data)
        } catch {
            // Silently fail
        } finally {
            setLoading(false)
        }
    }

    const updatePref = async (appId: string, field: 'email_enabled' | 'in_app_enabled', value: boolean) => {
        if (!prefs) return

        const currentPref = prefs.preferences[appId] || { email_enabled: false, in_app_enabled: false }
        const updatedPref = { ...currentPref, [field]: value }

        // Optimistic update
        setPrefs(prev => prev ? {
            ...prev,
            preferences: { ...prev.preferences, [appId]: updatedPref }
        } : null)

        setSaving(true)
        try {
            await api.put('/api/auth/notifications/preferences', {
                preferences: [{ app_id: appId, ...updatedPref }]
            })
        } catch {
            // Revert on error
            setPrefs(prev => prev ? {
                ...prev,
                preferences: { ...prev.preferences, [appId]: currentPref }
            } : null)
        } finally {
            setSaving(false)
        }
    }

    useEffect(() => {
        fetchPrefs()
    }, [])

    if (loading) {
        return (
            <div style={{ padding: '8px 0', color: theme.softText, fontSize: '0.85rem' }}>
                Loading preferences...
            </div>
        )
    }

    if (!prefs) {
        return null
    }

    return (
        <div style={{ fontSize: '0.85rem', color: theme.mutedText }}>
            {/* Global Email Toggle (Master Switch) */}
            <div style={{ paddingTop: '8px', borderTop: `1px solid ${theme.border}`, marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
                    <div>
                        <div style={{ fontWeight: 'bold', color: 'white', marginBottom: '4px' }}>Email Notifications</div>
                        <div style={{ fontSize: '0.75rem', color: theme.softText }}>Master switch</div>
                    </div>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                        <input
                            type="checkbox"
                            checked={globalEmailEnabled}
                            onChange={onGlobalEmailToggle}
                        />
                        <span style={{ color: 'white' }}>{globalEmailEnabled ? 'On' : 'Off'}</span>
                    </label>
                </div>
            </div>

            {/* Per-App Section Header */}
            <div
                onClick={() => setExpanded(!expanded)}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 0',
                    cursor: 'pointer',
                    borderTop: `1px solid ${theme.border}`,
                }}
            >
                <div style={{ fontWeight: 'bold', color: 'white' }}>Per-App Settings</div>
                <span style={{ color: theme.softText }}>{expanded ? '▼' : '▶'}</span>
            </div>

            {/* Per-App Toggles */}
            {expanded && (
                <div style={{ paddingTop: '4px' }}>
                    {/* Header Row */}
                    <div
                        style={{
                            display: 'grid',
                            gridTemplateColumns: '1fr 50px 50px',
                            gap: '8px',
                            marginBottom: '8px',
                            fontSize: '0.75rem',
                            color: theme.softText,
                        }}
                    >
                        <div>App</div>
                        <div style={{ textAlign: 'center' }}>Email</div>
                        <div style={{ textAlign: 'center' }}>In-App</div>
                    </div>

                    {/* App Rows */}
                    {prefs.apps.map((appId) => {
                        const appInfo = APP_LABELS[appId] || { icon: '📬', name: appId }
                        const appPrefs = prefs.preferences[appId] || { email_enabled: false, in_app_enabled: false }

                        return (
                            <div
                                key={appId}
                                style={{
                                    display: 'grid',
                                    gridTemplateColumns: '1fr 50px 50px',
                                    gap: '8px',
                                    alignItems: 'center',
                                    padding: '6px 0',
                                    borderTop: `1px solid ${theme.border}`,
                                }}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'white' }}>
                                    <span>{appInfo.icon}</span>
                                    <span style={{ fontSize: '0.8rem' }}>{appInfo.name}</span>
                                </div>
                                <div style={{ textAlign: 'center' }}>
                                    <input
                                        type="checkbox"
                                        checked={appPrefs.email_enabled}
                                        onChange={(e) => updatePref(appId, 'email_enabled', e.target.checked)}
                                        disabled={saving || !globalEmailEnabled}
                                        title={!globalEmailEnabled ? 'Enable master email toggle first' : undefined}
                                        style={{ cursor: saving || !globalEmailEnabled ? 'not-allowed' : 'pointer' }}
                                    />
                                </div>
                                <div style={{ textAlign: 'center' }}>
                                    <input
                                        type="checkbox"
                                        checked={appPrefs.in_app_enabled}
                                        onChange={(e) => updatePref(appId, 'in_app_enabled', e.target.checked)}
                                        disabled={saving}
                                        style={{ cursor: saving ? 'not-allowed' : 'pointer' }}
                                    />
                                </div>
                            </div>
                        )
                    })}

                    {/* Helper text */}
                    <div style={{ marginTop: '8px', fontSize: '0.7rem', color: theme.softText, fontStyle: 'italic' }}>
                        Email requires master toggle. In-app works independently.
                    </div>
                </div>
            )}
        </div>
    )
}
