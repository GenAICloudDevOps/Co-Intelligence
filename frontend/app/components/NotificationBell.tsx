'use client'

import React, { useState, useEffect, useRef } from 'react'
import { api } from '../services/api'

interface Notification {
    id: number
    app_id: string
    title: string
    message: string | null
    link: string | null
    is_read: boolean
    created_at: string
}

interface NotificationBellProps {
    theme: {
        panelBg: string
        panelAltBg: string
        border: string
        mutedText: string
        softText: string
        accent: string
        success: string
    }
}

const APP_ICONS: Record<string, string> = {
    'agentic-barista': '☕',
    'agentic-lms': '🎓',
    'insurance-claims': '🚗',
    'llms-fine-tuning': '🧪',
    'data-analysis': '📊',
}

export default function NotificationBell({ theme }: NotificationBellProps) {
    const [notifications, setNotifications] = useState<Notification[]>([])
    const [unreadCount, setUnreadCount] = useState(0)
    const [isOpen, setIsOpen] = useState(false)
    const [loading, setLoading] = useState(false)
    const dropdownRef = useRef<HTMLDivElement>(null)

    const fetchUnreadCount = async () => {
        try {
            const data = await api.get<{ count: number }>('/api/auth/notifications/unread-count')
            setUnreadCount(data.count)
        } catch {
            // Silently fail - user may not be authenticated
        }
    }

    const fetchNotifications = async () => {
        setLoading(true)
        try {
            const data = await api.get<{ notifications: Notification[] }>('/api/auth/notifications?limit=20')
            setNotifications(data.notifications)
        } catch {
            // Silently fail
        } finally {
            setLoading(false)
        }
    }

    const markAsRead = async (id: number) => {
        try {
            await api.put(`/api/auth/notifications/${id}/read`, {})
            setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n))
            setUnreadCount(prev => Math.max(0, prev - 1))
        } catch {
            // Silently fail
        }
    }

    const markAllAsRead = async () => {
        try {
            await api.put('/api/auth/notifications/read-all', {})
            setNotifications(prev => prev.map(n => ({ ...n, is_read: true })))
            setUnreadCount(0)
        } catch {
            // Silently fail
        }
    }

    const handleNotificationClick = (notification: Notification) => {
        if (!notification.is_read) {
            markAsRead(notification.id)
        }
        if (notification.link) {
            window.open(notification.link, '_blank')
        }
        setIsOpen(false)
    }

    const formatTime = (dateStr: string) => {
        const date = new Date(dateStr)
        const now = new Date()
        const diffMs = now.getTime() - date.getTime()
        const diffMins = Math.floor(diffMs / 60000)
        const diffHours = Math.floor(diffMs / 3600000)
        const diffDays = Math.floor(diffMs / 86400000)

        if (diffMins < 1) return 'Just now'
        if (diffMins < 60) return `${diffMins}m ago`
        if (diffHours < 24) return `${diffHours}h ago`
        if (diffDays < 7) return `${diffDays}d ago`
        return date.toLocaleDateString()
    }

    // Fetch unread count on mount and periodically
    useEffect(() => {
        fetchUnreadCount()
        const interval = setInterval(fetchUnreadCount, 30000) // Every 30 seconds
        return () => clearInterval(interval)
    }, [])

    // Fetch full list when dropdown opens
    useEffect(() => {
        if (isOpen) {
            fetchNotifications()
        }
    }, [isOpen])

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    return (
        <div ref={dropdownRef} style={{ position: 'relative' }}>
            {/* Bell Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                style={{
                    position: 'relative',
                    padding: '8px 12px',
                    background: theme.panelBg,
                    border: `1px solid ${theme.border}`,
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontSize: '1.2rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                }}
                title="Notifications"
            >
                🔔
                {unreadCount > 0 && (
                    <span
                        style={{
                            position: 'absolute',
                            top: '-4px',
                            right: '-4px',
                            background: '#ef4444',
                            color: 'white',
                            fontSize: '0.7rem',
                            fontWeight: 'bold',
                            borderRadius: '50%',
                            width: '18px',
                            height: '18px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                        }}
                    >
                        {unreadCount > 9 ? '9+' : unreadCount}
                    </span>
                )}
            </button>

            {/* Dropdown */}
            {isOpen && (
                <div
                    style={{
                        position: 'absolute',
                        top: '45px',
                        right: '0',
                        width: '340px',
                        maxHeight: '400px',
                        background: theme.panelBg,
                        border: `1px solid ${theme.border}`,
                        borderRadius: '12px',
                        boxShadow: '0 10px 40px rgba(0,0,0,0.3)',
                        zIndex: 200,
                        overflow: 'hidden',
                    }}
                >
                    {/* Header */}
                    <div
                        style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: '14px 16px',
                            borderBottom: `1px solid ${theme.border}`,
                        }}
                    >
                        <span style={{ fontWeight: 'bold', color: 'white' }}>Notifications</span>
                        {unreadCount > 0 && (
                            <button
                                onClick={markAllAsRead}
                                style={{
                                    background: 'transparent',
                                    border: 'none',
                                    color: theme.accent,
                                    fontSize: '0.85rem',
                                    cursor: 'pointer',
                                }}
                            >
                                Mark all read
                            </button>
                        )}
                    </div>

                    {/* Notification List */}
                    <div style={{ maxHeight: '340px', overflowY: 'auto' }}>
                        {loading ? (
                            <div style={{ padding: '20px', textAlign: 'center', color: theme.mutedText }}>
                                Loading...
                            </div>
                        ) : notifications.length === 0 ? (
                            <div style={{ padding: '30px', textAlign: 'center', color: theme.softText }}>
                                <div style={{ fontSize: '2rem', marginBottom: '8px' }}>🔔</div>
                                No notifications yet
                            </div>
                        ) : (
                            notifications.map((notification) => (
                                <div
                                    key={notification.id}
                                    onClick={() => handleNotificationClick(notification)}
                                    style={{
                                        padding: '12px 16px',
                                        borderBottom: `1px solid ${theme.border}`,
                                        cursor: notification.link ? 'pointer' : 'default',
                                        background: notification.is_read ? 'transparent' : theme.panelAltBg,
                                        transition: 'background 0.2s',
                                    }}
                                    onMouseEnter={(e) => {
                                        e.currentTarget.style.background = theme.panelAltBg
                                    }}
                                    onMouseLeave={(e) => {
                                        e.currentTarget.style.background = notification.is_read ? 'transparent' : theme.panelAltBg
                                    }}
                                >
                                    <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                                        <span style={{ fontSize: '1.2rem' }}>
                                            {APP_ICONS[notification.app_id] || '📬'}
                                        </span>
                                        <div style={{ flex: 1 }}>
                                            <div
                                                style={{
                                                    fontWeight: notification.is_read ? 'normal' : 'bold',
                                                    color: 'white',
                                                    marginBottom: '4px',
                                                    fontSize: '0.9rem',
                                                }}
                                            >
                                                {notification.title}
                                            </div>
                                            {notification.message && (
                                                <div style={{ color: theme.mutedText, fontSize: '0.8rem', marginBottom: '4px' }}>
                                                    {notification.message}
                                                </div>
                                            )}
                                            <div style={{ color: theme.softText, fontSize: '0.75rem' }}>
                                                {formatTime(notification.created_at)}
                                            </div>
                                        </div>
                                        {!notification.is_read && (
                                            <span
                                                style={{
                                                    width: '8px',
                                                    height: '8px',
                                                    background: theme.accent,
                                                    borderRadius: '50%',
                                                    flexShrink: 0,
                                                    marginTop: '6px',
                                                }}
                                            />
                                        )}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
