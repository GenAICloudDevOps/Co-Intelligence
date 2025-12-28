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
    globalEmailEnabled: boolean
    globalSlackEnabled: boolean
}

const APP_LABELS: Record<string, { icon: string; name: string }> = {
    'agentic-barista': { icon: '☕', name: 'Agentic Barista' },
    'agentic-lms': { icon: '🎓', name: 'Agentic LMS' },
    'insurance-claims': { icon: '🚗', name: 'Insurance Claims' },
    'llms-fine-tuning': { icon: '🧪', name: 'LLMs Fine-Tuning' },
    'data-analysis': { icon: '📊', name: 'Data Analysis' },
}

export default function NotificationPreferences({ theme, globalEmailEnabled, globalSlackEnabled }: NotificationPreferencesProps) {
    const [prefs, setPrefs] = useState<NotificationPreferences | null>(null)
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [isPerAppOpen, setIsPerAppOpen] = useState(false)

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
            <button
                type="button"
                onClick={() => setIsPerAppOpen((prev) => !prev)}
                aria-expanded={isPerAppOpen}
                aria-controls="per-app-settings-panel"
                style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'flex-start',
                    gap: '8px',
                    background: 'transparent',
                    border: 'none',
                    padding: '0 0 8px 0',
                    borderBottom: `1px solid ${theme.border}`,
                    color: 'white',
                    cursor: 'pointer',
                    fontWeight: 'bold',
                    textAlign: 'left',
                }}
            >
                <span style={{ color: theme.softText, fontSize: '0.9rem', width: '14px' }}>{isPerAppOpen ? '▾' : '▸'}</span>
                <span>Per-App Settings</span>
            </button>

            <div
                id="per-app-settings-panel"
                aria-hidden={!isPerAppOpen}
                style={{
                    marginTop: isPerAppOpen ? '12px' : '0',
                    maxHeight: isPerAppOpen ? '800px' : '0',
                    opacity: isPerAppOpen ? 1 : 0,
                    overflow: 'hidden',
                    pointerEvents: isPerAppOpen ? 'auto' : 'none',
                    transition: 'max-height 220ms ease, opacity 200ms ease, margin-top 200ms ease',
                }}
            >
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
                                    disabled={saving || !globalEmailEnabled || !isPerAppOpen}
                                    title={!globalEmailEnabled ? 'Enable master email toggle first' : undefined}
                                    style={{ cursor: saving || !globalEmailEnabled ? 'not-allowed' : 'pointer' }}
                                />
                            </div>
                            <div style={{ textAlign: 'center' }}>
                                <input
                                    type="checkbox"
                                    checked={appPrefs.in_app_enabled}
                                    onChange={(e) => updatePref(appId, 'in_app_enabled', e.target.checked)}
                                    disabled={saving || !isPerAppOpen}
                                    style={{ cursor: saving ? 'not-allowed' : 'pointer' }}
                                />
                            </div>
                            <div style={{ textAlign: 'center' }}>
                                <input
                                    type="checkbox"
                                    checked={appPrefs.slack_enabled}
                                    onChange={(e) => updatePref(appId, 'slack_enabled', e.target.checked)}
                                    disabled={saving || !globalSlackEnabled || !isPerAppOpen}
                                    title={!globalSlackEnabled ? 'Enable master Slack toggle first' : undefined}
                                    style={{ cursor: saving || !globalSlackEnabled ? 'not-allowed' : 'pointer' }}
                                />
                            </div>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}
