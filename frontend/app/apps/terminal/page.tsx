'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import type { Terminal as XTermTerminal } from 'xterm'
import type { FitAddon as XTermFitAddon } from 'xterm-addon-fit'
import AppHeader from '@/app/design-system/components/AppHeader'
import { useAuth } from '@/app/hooks/useAuth'
import { API_URL } from '@/app/services/api'

type ConnectionStatus = 'connecting' | 'connected' | 'error' | 'closed'

function buildWsUrl(): string {
  const base = (API_URL || (typeof window !== 'undefined' ? window.location.origin : '')).replace(/\/$/, '')
  const protocol = base.startsWith('https') ? 'wss' : 'ws'
  const host = base.replace(/^https?:\/\//, '')
  return `${protocol}://${host}/api/apps/terminal/ws`
}

export default function TerminalApp() {
  const { user, initializing } = useAuth(true)
  const containerRef = useRef<HTMLDivElement>(null)
  const terminalRef = useRef<XTermTerminal | null>(null)
  const fitRef = useRef<XTermFitAddon | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const [error, setError] = useState<string | null>(null)

  const statusLabel = useMemo(() => {
    if (status === 'connected') return 'Connected'
    if (status === 'error') return 'Error'
    if (status === 'closed') return 'Closed'
    return 'Connecting'
  }, [status])

  useEffect(() => {
    if (initializing || !user) return
    const container = containerRef.current
    if (!container) return

    let disposed = false
    let cleanup = () => {}

    const setup = async () => {
      const [{ Terminal }, { FitAddon }] = await Promise.all([
        import('xterm'),
        import('xterm-addon-fit')
      ])
      if (disposed) return

      const term = new Terminal({
        cursorBlink: true,
        fontFamily: "'SF Mono', Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
        fontSize: 14,
        theme: {
          background: '#0b0f1a',
          foreground: '#e2e8f0',
          cursor: '#38bdf8',
          selectionBackground: 'rgba(56, 189, 248, 0.25)'
        },
        scrollback: 2000
      })
      const fit = new FitAddon()
      term.loadAddon(fit)
      term.open(container)
      fit.fit()
      term.focus()

      terminalRef.current = term
      fitRef.current = fit

      const ws = new WebSocket(buildWsUrl())
      wsRef.current = ws

      const sendResize = () => {
        if (ws.readyState !== WebSocket.OPEN) return
        fit.fit()
        ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }))
      }

      const handleResize = () => sendResize()
      window.addEventListener('resize', handleResize)

      const dataDisposable = term.onData((data) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'input', data }))
        }
      })

      ws.onopen = () => {
        if (disposed) return
        setStatus('connected')
        setError(null)
        sendResize()
      }

      ws.onmessage = (event) => {
        if (disposed) return
        try {
          const payload = JSON.parse(event.data)
          if (payload.type === 'output') {
            term.write(payload.data || '')
          } else if (payload.type === 'error') {
            setStatus('error')
            setError(payload.message || 'Terminal error')
          }
        } catch {
          term.write(event.data)
        }
      }

      ws.onerror = () => {
        if (disposed) return
        setStatus('error')
        setError('WebSocket error')
      }

      ws.onclose = () => {
        if (disposed) return
        setStatus('closed')
      }

      cleanup = () => {
        window.removeEventListener('resize', handleResize)
        dataDisposable.dispose()
        try {
          ws.close()
        } catch {
          // ignore
        }
        term.dispose()
        terminalRef.current = null
        fitRef.current = null
        wsRef.current = null
      }

      if (disposed) {
        cleanup()
      }
    }

    setup()

    return () => {
      disposed = true
      cleanup()
    }
  }, [initializing, user])

  if (initializing || !user) {
    return (
      <div style={{ minHeight: '100vh', background: '#0f172a', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        Loading...
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0a0f1e 0%, #14132b 100%)', color: 'white' }}>
      <AppHeader appName="Terminal" />

      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '1.8rem', fontWeight: 800 }}>Ubuntu 22.04 Terminal</h1>
            <p style={{ margin: '6px 0 0', color: '#94a3b8' }}>
              Isolated session with full internet access. No access to other apps.
            </p>
          </div>
          <div style={{
            padding: '6px 12px',
            borderRadius: '999px',
            background: status === 'connected' ? 'rgba(34, 197, 94, 0.2)' : 'rgba(248, 113, 113, 0.2)',
            color: status === 'connected' ? '#22c55e' : '#f87171',
            fontWeight: 700,
            fontSize: '0.85rem'
          }}>
            {statusLabel}
          </div>
        </div>

        {error && (
          <div style={{ marginBottom: '12px', padding: '10px 12px', border: '1px solid #7f1d1d', background: '#450a0a', borderRadius: '8px', color: '#fecaca' }}>
            {error}
          </div>
        )}

        <div
          style={{
            background: '#0b0f1a',
            border: '1px solid rgba(148, 163, 184, 0.2)',
            borderRadius: '16px',
            padding: '12px',
            boxShadow: '0 20px 40px rgba(15, 23, 42, 0.6)',
            minHeight: '70vh'
          }}
        >
          <div
            ref={containerRef}
            style={{ width: '100%', height: '70vh' }}
          />
        </div>
      </div>
    </div>
  )
}
