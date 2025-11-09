interface CardProps {
  children: React.ReactNode
  className?: string
  padding?: 'sm' | 'md' | 'lg'
  hover?: boolean
}

export default function Card({ children, className = '', padding = 'md', hover = false }: CardProps) {
  const paddings = {
    sm: '16px',
    md: '24px',
    lg: '32px'
  }
  
  return (
    <div
      style={{
        background: '#1e293b',
        borderRadius: '12px',
        padding: paddings[padding],
        border: '1px solid #334155',
        transition: hover ? 'transform 0.2s, box-shadow 0.2s' : 'none'
      }}
      className={className}
      onMouseEnter={(e) => {
        if (hover) {
          e.currentTarget.style.transform = 'translateY(-4px)'
          e.currentTarget.style.boxShadow = '0 8px 16px rgba(0,0,0,0.3)'
        }
      }}
      onMouseLeave={(e) => {
        if (hover) {
          e.currentTarget.style.transform = 'translateY(0)'
          e.currentTarget.style.boxShadow = 'none'
        }
      }}
    >
      {children}
    </div>
  )
}
