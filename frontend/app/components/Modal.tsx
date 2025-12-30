interface ModalProps {
  isOpen: boolean
  onClose: () => void
  children: React.ReactNode
  title?: string
  maxWidth?: string
}

export default function Modal({ isOpen, onClose, children, title, maxWidth = '500px' }: ModalProps) {
  if (!isOpen) return null

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0, 0, 0, 0.85)',
        backdropFilter: 'blur(12px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        animation: 'fadeIn 0.3s ease'
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(49, 46, 129, 0.95) 100%)',
          backdropFilter: 'blur(20px)',
          padding: '40px',
          borderRadius: '24px',
          maxWidth,
          width: '90%',
          border: '2px solid rgba(139, 92, 246, 0.4)',
          boxShadow: '0 20px 60px rgba(139, 92, 246, 0.4), 0 0 80px rgba(99, 102, 241, 0.3)',
          maxHeight: '90vh',
          overflow: 'auto',
          animation: 'slideUp 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
          position: 'relative'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Decorative gradient border effect */}
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '4px',
          background: 'linear-gradient(90deg, #6366f1 0%, #8b5cf6 33%, #ec4899 66%, #6366f1 100%)',
          borderRadius: '24px 24px 0 0',
          animation: 'shimmer 3s linear infinite',
          backgroundSize: '200% 100%'
        }} />
        
        {/* Animated corner accents */}
        <div style={{
          position: 'absolute',
          top: '20px',
          right: '20px',
          width: '40px',
          height: '40px',
          border: '3px solid rgba(139, 92, 246, 0.5)',
          borderRadius: '50%',
          animation: 'pulse 2s ease-in-out infinite'
        }} />
        
        <div style={{
          position: 'absolute',
          bottom: '20px',
          left: '20px',
          width: '30px',
          height: '30px',
          border: '3px solid rgba(236, 72, 153, 0.5)',
          borderRadius: '50%',
          animation: 'pulse 2s ease-in-out infinite 1s'
        }} />
        
        {title && (
          <h2 style={{ 
            marginBottom: '28px', 
            fontSize: '1.75rem', 
            fontWeight: '800',
            background: 'linear-gradient(135deg, #ffffff 0%, #c7d2fe 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            textShadow: '0 2px 20px rgba(255, 255, 255, 0.2)',
            position: 'relative',
            zIndex: 1
          }}>
            {title}
          </h2>
        )}
        
        <div style={{ position: 'relative', zIndex: 1 }}>
          {children}
        </div>
      </div>
      
      <style jsx>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes slideUp {
          from { 
            opacity: 0;
            transform: translateY(40px) scale(0.95);
          }
          to { 
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
        @keyframes shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
        @keyframes pulse {
          0%, 100% { 
            transform: scale(1);
            opacity: 0.5;
          }
          50% { 
            transform: scale(1.1);
            opacity: 0.8;
          }
        }
      `}</style>
    </div>
  )
}
