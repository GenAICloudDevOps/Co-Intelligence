'use client'

import React, { useState, useEffect } from 'react'
import { api } from '../services/api'

interface NotificationPreferences {
    global_email_enabled: boolean
    global_slack_enabled?: boolean
    apps: string[]
    preferences: Record<string, { email_enabled: boolean; in_app_enabled: boolean; slack_enabled: boolean }>
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
    onGlobalSlackToggle: () => void
    globalSlackEnabled: boolean
}

const APP_LABELS: Record<string, { icon: string; name: string }> = {
    'agentic-barista': { icon: '☕', name: 'Agentic Barista' },
    'agentic-lms': { icon: '🎓', name: 'Agentic LMS' },
    'insurance-claims': { icon: '🚗', name: 'Insurance Claims' },
    'llms-fine-tuning': { icon: '🧪', name: 'LLMs Fine-Tuning' },
    'data-analysis': { icon: '📊', name: 'Data Analysis' },
}

export default function NotificationPreferences({ theme, onGlobalEmailToggle, globalEmailEnabled, onGlobalSlackToggle, globalSlackEnabled }: NotificationPreferencesProps) {
    const [prefs, setPrefs] = useState<NotificationPreferences | null>(null)
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)

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

    const updatePref = async (appId: string, field: 'email_enabled' | 'in_app_enabled' | 'slack_enabled', value: boolean) => {
        if (!prefs) return

        const currentPref = prefs.preferences[appId] || { email_enabled: false, in_app_enabled: false, slack_enabled: false }
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
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(400px, 1fr) 280px', gap: '24px', alignItems: 'start' }}>
                {/* Left Column: Per-App Settings */}
                <div>
                    <div style={{
                        fontWeight: 'bold',
                        color: 'white',
                        marginBottom: '12px',
                        paddingBottom: '8px',
                        borderBottom: `1px solid ${theme.border}`
                    }}>
                        Per-App Settings
                    </div>

                    {/* Header Row */}
                    <div
                        style={{
                            display: 'grid',
                            gridTemplateColumns: '1fr 60px 60px 60px',
                            gap: '8px',
                            marginBottom: '8px',
                            fontSize: '0.75rem',
                            color: theme.softText,
                        }}
                    >
                        <div>App</div>
                        <div style={{ textAlign: 'center' }}>Email</div>
                        <div style={{ textAlign: 'center' }}>In-App</div>
                        <div style={{ textAlign: 'center' }}>Slack</div>
                    </div>

                    {/* App Rows */}
                    {prefs.apps.map((appId) => {
                        const appInfo = APP_LABELS[appId] || { icon: '📬', name: appId }
                        const appPrefs = prefs.preferences[appId] || { email_enabled: false, in_app_enabled: false, slack_enabled: false }

                        return (
                            <div
                                key={appId}
                                style={{
                                    display: 'grid',
                                    gridTemplateColumns: '1fr 60px 60px 60px',
                                    gap: '8px',
                                    alignItems: 'center',
                                    padding: '8px 0',
                                    borderTop: `1px solid ${theme.border}`,
                                }}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'white' }}>
                                    <span style={{ fontSize: '1.2em' }}>{appInfo.icon}</span>
                                    <span style={{ fontSize: '0.85rem' }}>{appInfo.name}</span>
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
                                <div style={{ textAlign: 'center' }}>
                                    <input
                                        type="checkbox"
                                        checked={appPrefs.slack_enabled}
                                        onChange={(e) => updatePref(appId, 'slack_enabled', e.target.checked)}
                                        disabled={saving || !globalSlackEnabled}
                                        title={!globalSlackEnabled ? 'Enable master Slack toggle first' : undefined}
                                        style={{ cursor: saving || !globalSlackEnabled ? 'not-allowed' : 'pointer' }}
                                    />
                                </div>
                            </div>
                        )
                    })}
                </div>

                {/* Right Column: Global Switches */}
                <div style={{ display: 'grid', gap: '12px' }}>
                    <div style={{
                        padding: '16px',
                        background: theme.panelAltBg,
                        borderRadius: '8px',
                        border: `1px solid ${theme.border}`
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                            <div style={{ fontWeight: 'bold', color: 'white' }}>Email Notifications</div>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                                <input
                                    type="checkbox"
                                    checked={globalEmailEnabled}
                                    onChange={onGlobalEmailToggle}
                                />
                                <span style={{ color: 'white' }}>{globalEmailEnabled ? 'On' : 'Off'}</span>
                            </label>
                        </div>

                        <div style={{ fontSize: '0.75rem', color: theme.softText, lineHeight: '1.4' }}>
                            <div>Master switch controls email delivery across all apps.</div>
                            <div style={{ marginTop: '12px', fontStyle: 'italic', opacity: 0.8 }}>
                                Note: In-app alerts have their own toggle.
                            </div>
                        </div>
                    </div>

                    <div style={{
                        padding: '16px',
                        background: theme.panelAltBg,
                        borderRadius: '8px',
                        border: `1px solid ${theme.border}`
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                            <div style={{ fontWeight: 'bold', color: 'white' }}>Slack Notifications</div>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                                <input
                                    type="checkbox"
                                    checked={globalSlackEnabled}
                                    onChange={onGlobalSlackToggle}
                                />
                                <span style={{ color: 'white' }}>{globalSlackEnabled ? 'On' : 'Off'}</span>
                            </label>
                        </div>

                        <div style={{ fontSize: '0.75rem', color: theme.softText, lineHeight: '1.4' }}>
                            <div>Master switch controls Slack delivery across all apps.</div>
                            <div style={{ marginTop: '12px', fontStyle: 'italic', opacity: 0.8 }}>
                                Per-app Slack toggles default to off.
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
