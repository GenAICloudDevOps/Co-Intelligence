import Card from './Card'
import type { AppConfig } from '../config/apps'

interface AppCardProps {
  app: AppConfig
  onLaunch: (app: AppConfig) => void
}

export default function AppCard({ app, onLaunch }: AppCardProps) {
  const isActive = app.status === 'active'
  
  return (
    <Card padding="lg" hover={isActive}>
      <div style={{ position: 'relative' }}>
        <div
          style={{
            position: 'absolute',
            top: '-12px',
            right: '-12px',
            padding: '4px 12px',
            background: isActive ? '#10b981' : '#64748b',
            borderRadius: '12px',
            fontSize: '0.75rem',
            fontWeight: '600'
          }}
        >
          {app.status}
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '16px' }}>
          <div
            style={{
              width: '48px',
              height: '48px',
              background: isActive ? app.color : '#64748b',
              borderRadius: '12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '24px',
              flexShrink: 0
            }}
          >
            {app.icon}
          </div>
          <h3 style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: 0 }}>{app.name}</h3>
        </div>
        
        <p style={{ color: '#94a3b8', lineHeight: '1.6', marginBottom: '24px', fontSize: '0.95rem' }}>
          {app.description.map((line, i) => (
            <span key={i}>
              • {line}
              <br />
            </span>
          ))}
        </p>
        
        <button
          onClick={() => onLaunch(app)}
          disabled={!isActive}
          style={{
            padding: '12px 28px',
            background: isActive ? app.color : '#64748b',
            border: 'none',
            borderRadius: '8px',
            color: 'white',
            cursor: isActive ? 'pointer' : 'not-allowed',
            fontWeight: '600',
            fontSize: '0.95rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            opacity: isActive ? 1 : 0.6
          }}
        >
          {isActive ? 'Launch' : 'Coming Soon'} {isActive && <span>↗</span>}
        </button>
      </div>
    </Card>
  )
}
