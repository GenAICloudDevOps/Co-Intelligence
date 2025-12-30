import Card from './Card'
import type { AppConfig } from '../../config/apps'

interface AppCardProps {
  app: AppConfig
  onLaunch: (app: AppConfig) => void
}

export default function AppCard({ app, onLaunch }: AppCardProps) {
  const isActive = app.status === 'active'
  
  return (
    <Card padding="lg" hover={isActive}>
      <div style={{ position: 'relative' }}>
        {/* Status Badge */}
        <div
          style={{
            position: 'absolute',
            top: '-12px',
            right: '-12px',
            padding: '6px 16px',
            background: isActive 
              ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' 
              : 'linear-gradient(135deg, #64748b 0%, #475569 100%)',
            borderRadius: '20px',
            fontSize: '0.75rem',
            fontWeight: '700',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            boxShadow: isActive 
              ? '0 4px 15px rgba(16, 185, 129, 0.5), 0 0 20px rgba(16, 185, 129, 0.3)' 
              : '0 4px 12px rgba(100, 116, 139, 0.4)',
            border: isActive 
              ? '2px solid rgba(16, 185, 129, 0.6)' 
              : '2px solid rgba(100, 116, 139, 0.4)',
            animation: isActive ? 'pulse-glow 2s ease-in-out infinite' : 'none'
          }}
        >
          {app.status}
        </div>
        
        {/* Icon and Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '20px' }}>
          <div
            style={{
              width: '64px',
              height: '64px',
              background: isActive 
                ? `linear-gradient(135deg, ${app.color} 0%, ${app.color}dd 100%)` 
                : 'linear-gradient(135deg, #64748b 0%, #475569 100%)',
              borderRadius: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '32px',
              flexShrink: 0,
              boxShadow: isActive 
                ? `0 8px 30px ${app.color}50, 0 0 40px ${app.color}30` 
                : '0 8px 24px rgba(100, 116, 139, 0.4)',
              border: '3px solid rgba(255, 255, 255, 0.15)',
              transition: 'all 0.3s ease',
              position: 'relative',
              overflow: 'hidden'
            }}
          >
            {/* Icon glow effect */}
            {isActive && (
              <div style={{
                position: 'absolute',
                top: '-50%',
                left: '-50%',
                width: '200%',
                height: '200%',
                background: `radial-gradient(circle, ${app.color}40 0%, transparent 70%)`,
                animation: 'rotate 4s linear infinite'
              }} />
            )}
            <span style={{ position: 'relative', zIndex: 1 }}>{app.icon}</span>
          </div>
          
          <h3 style={{ 
            fontSize: '1.75rem', 
            fontWeight: '800', 
            margin: 0,
            background: 'linear-gradient(135deg, #ffffff 0%, #c7d2fe 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            textShadow: '0 2px 10px rgba(255, 255, 255, 0.1)'
          }}>
            {app.name}
          </h3>
        </div>
        
        {/* Description */}
        <p style={{ 
          color: '#cbd5e1', 
          lineHeight: '1.8', 
          marginBottom: '28px', 
          fontSize: '1rem',
          fontWeight: '400'
        }}>
          {app.description.map((line, i) => (
            <span key={i}>
              <span style={{ 
                color: '#8b5cf6', 
                fontWeight: '700',
                marginRight: '8px',
                fontSize: '1.2rem'
              }}>
                •
              </span>
              {line}
              <br />
            </span>
          ))}
        </p>
        
        {/* Launch Button */}
        <button
          onClick={() => onLaunch(app)}
          disabled={!isActive}
          style={{
            padding: '14px 32px',
            background: isActive 
              ? `linear-gradient(135deg, ${app.color} 0%, ${app.color}cc 100%)` 
              : 'linear-gradient(135deg, #64748b 0%, #475569 100%)',
            border: 'none',
            borderRadius: '12px',
            color: 'white',
            cursor: isActive ? 'pointer' : 'not-allowed',
            fontWeight: '700',
            fontSize: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            opacity: isActive ? 1 : 0.6,
            boxShadow: isActive 
              ? `0 6px 25px ${app.color}60, 0 0 30px ${app.color}30` 
              : '0 6px 20px rgba(100, 116, 139, 0.4)',
            transition: 'all 0.3s ease',
            textTransform: 'uppercase',
            letterSpacing: '1px',
            position: 'relative',
            overflow: 'hidden'
          }}
          onMouseEnter={(e) => {
            if (isActive) {
              e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)'
              e.currentTarget.style.boxShadow = `0 8px 35px ${app.color}80, 0 0 50px ${app.color}50`
            }
          }}
          onMouseLeave={(e) => {
            if (isActive) {
              e.currentTarget.style.transform = 'translateY(0) scale(1)'
              e.currentTarget.style.boxShadow = `0 6px 25px ${app.color}60, 0 0 30px ${app.color}30`
            }
          }}
        >
          {/* Button shine effect */}
          {isActive && (
            <div style={{
              position: 'absolute',
              top: '-50%',
              left: '-50%',
              width: '200%',
              height: '200%',
              background: 'linear-gradient(45deg, transparent 30%, rgba(255, 255, 255, 0.2) 50%, transparent 70%)',
              transform: 'translateX(-100%)',
              animation: 'shine 3s ease-in-out infinite'
            }} />
          )}
          <span style={{ position: 'relative', zIndex: 1 }}>
            {isActive ? 'Launch App' : 'Coming Soon'}
          </span>
          {isActive && <span style={{ fontSize: '1.2rem', position: 'relative', zIndex: 1 }}>↗</span>}
        </button>
      </div>
      
      <style jsx>{`
        @keyframes pulse-glow {
          0%, 100% { 
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.5), 0 0 20px rgba(16, 185, 129, 0.3);
          }
          50% { 
            box-shadow: 0 4px 20px rgba(16, 185, 129, 0.7), 0 0 30px rgba(16, 185, 129, 0.5);
          }
        }
        @keyframes rotate {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes shine {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
      `}</style>
    </Card>
  )
}
