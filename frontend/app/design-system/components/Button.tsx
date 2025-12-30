interface ButtonProps {
  children: React.ReactNode
  onClick?: () => void
  disabled?: boolean
  variant?: 'primary' | 'secondary' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  fullWidth?: boolean
}

export default function Button({
  children,
  onClick,
  disabled = false,
  variant = 'primary',
  size = 'md',
  fullWidth = false
}: ButtonProps) {
  const variants = {
    primary: {
      background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
      hoverBackground: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
      shadow: '0 4px 20px rgba(99, 102, 241, 0.5), 0 0 30px rgba(139, 92, 246, 0.3)',
      hoverShadow: '0 6px 30px rgba(99, 102, 241, 0.7), 0 0 50px rgba(139, 92, 246, 0.5)'
    },
    secondary: {
      background: 'linear-gradient(135deg, #64748b 0%, #475569 100%)',
      hoverBackground: 'linear-gradient(135deg, #475569 0%, #334155 100%)',
      shadow: '0 4px 20px rgba(100, 116, 139, 0.5), 0 0 30px rgba(100, 116, 139, 0.2)',
      hoverShadow: '0 6px 30px rgba(100, 116, 139, 0.7), 0 0 50px rgba(100, 116, 139, 0.4)'
    },
    danger: {
      background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
      hoverBackground: 'linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)',
      shadow: '0 4px 20px rgba(239, 68, 68, 0.5), 0 0 30px rgba(220, 38, 38, 0.3)',
      hoverShadow: '0 6px 30px rgba(239, 68, 68, 0.7), 0 0 50px rgba(220, 38, 38, 0.5)'
    }
  }
  
  const sizes = {
    sm: { padding: '8px 16px', fontSize: '0.875rem' },
    md: { padding: '12px 24px', fontSize: '1rem' },
    lg: { padding: '16px 32px', fontSize: '1.125rem' }
  }
  
  const currentVariant = variants[variant]
  const currentSize = sizes[size]
  
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        background: currentVariant.background,
        color: 'white',
        border: 'none',
        borderRadius: '12px',
        padding: currentSize.padding,
        fontSize: currentSize.fontSize,
        fontWeight: '700',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        width: fullWidth ? '100%' : 'auto',
        boxShadow: currentVariant.shadow,
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '8px',
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
        position: 'relative',
        overflow: 'hidden'
      }}
      onMouseEnter={(e) => {
        if (!disabled) {
          e.currentTarget.style.background = currentVariant.hoverBackground
          e.currentTarget.style.boxShadow = currentVariant.hoverShadow
          e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)'
        }
      }}
      onMouseLeave={(e) => {
        if (!disabled) {
          e.currentTarget.style.background = currentVariant.background
          e.currentTarget.style.boxShadow = currentVariant.shadow
          e.currentTarget.style.transform = 'translateY(0) scale(1)'
        }
      }}
    >
      {/* Shine effect overlay */}
      {!disabled && (
        <div style={{
          position: 'absolute',
          top: '-50%',
          left: '-50%',
          width: '200%',
          height: '200%',
          background: 'linear-gradient(45deg, transparent 30%, rgba(255, 255, 255, 0.15) 50%, transparent 70%)',
          transform: 'translateX(-100%)',
          animation: 'shine 3s ease-in-out infinite'
        }} />
      )}
      
      <span style={{ position: 'relative', zIndex: 1 }}>
        {children}
      </span>
      
      <style jsx>{`
        @keyframes shine {
          0% { transform: translateX(-100%) rotate(45deg); }
          100% { transform: translateX(100%) rotate(45deg); }
        }
      `}</style>
    </button>
  )
}
