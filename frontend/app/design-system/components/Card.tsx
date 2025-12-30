interface CardProps {
  children: React.ReactNode
  className?: string
  padding?: 'sm' | 'md' | 'lg'
  hover?: boolean
  onClick?: () => void
}

export default function Card({ children, className = '', padding = 'md', hover = false, onClick }: CardProps) {
  const paddings = {
    sm: '16px',
    md: '24px',
    lg: '32px'
  }
  
  return (
    <div
      onClick={onClick}
      style={{
        background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(139, 92, 246, 0.15) 100%)',
        backdropFilter: 'blur(10px)',
        borderRadius: '16px',
        padding: paddings[padding],
        border: '2px solid rgba(139, 92, 246, 0.4)',
        boxShadow: '0 4px 20px rgba(139, 92, 246, 0.2), 0 0 40px rgba(99, 102, 241, 0.1)',
        transition: hover ? 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)' : 'none',
        position: 'relative',
        overflow: 'hidden',
        cursor: onClick ? 'pointer' : 'default'
      }}
      className={className}
      onMouseEnter={(e) => {
        if (hover) {
          e.currentTarget.style.transform = 'translateY(-8px) scale(1.02)'
          e.currentTarget.style.boxShadow = '0 12px 40px rgba(139, 92, 246, 0.4), 0 0 60px rgba(99, 102, 241, 0.3)'
          e.currentTarget.style.borderColor = 'rgba(167, 139, 250, 0.7)'
        }
      }}
      onMouseLeave={(e) => {
        if (hover) {
          e.currentTarget.style.transform = 'translateY(0) scale(1)'
          e.currentTarget.style.boxShadow = '0 4px 20px rgba(139, 92, 246, 0.2), 0 0 40px rgba(99, 102, 241, 0.1)'
          e.currentTarget.style.borderColor = 'rgba(139, 92, 246, 0.4)'
        }
      }}
    >
      {/* Animated gradient background */}
      <div style={{
        position: 'absolute',
        top: '-50%',
        left: '-50%',
        width: '200%',
        height: '200%',
        background: 'radial-gradient(circle at center, rgba(167, 139, 250, 0.15) 0%, transparent 60%)',
        pointerEvents: 'none',
        opacity: 0.5
      }} />
      
      <div style={{ position: 'relative', zIndex: 1 }}>
        {children}
      </div>
    </div>
  )
}
