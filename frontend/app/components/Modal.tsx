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
        background: 'rgba(0,0,0,0.8)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: '#1e293b',
          padding: '32px',
          borderRadius: '16px',
          maxWidth,
          width: '90%',
          border: '1px solid #334155',
          maxHeight: '90vh',
          overflow: 'auto'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {title && (
          <h2 style={{ marginBottom: '24px', fontSize: '1.5rem', fontWeight: 'bold' }}>
            {title}
          </h2>
        )}
        {children}
      </div>
    </div>
  )
}
