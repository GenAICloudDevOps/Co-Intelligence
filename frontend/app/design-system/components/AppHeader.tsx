'use client';

import { useEffect } from 'react';
import { Coffee, ShoppingCart, User, LogOut, LogIn } from 'lucide-react';
import { ModelSelector } from '../../config/models';
import { useAuth } from '../../hooks/useAuth';
import { useModel } from '../../components/ModelProvider';
import { useRouter } from 'next/navigation';

interface AppHeaderProps {
  appName: string;
  requireAuth?: boolean;
  showModelSelector?: boolean;
  showCart?: boolean;
  selectedModel?: string;
  onModelChange?: (model: string) => void;
  cartCount?: number;
}

export default function AppHeader({
  appName,
  requireAuth = true,
  showModelSelector = false,
  showCart = false,
  selectedModel: selectedModelProp,
  onModelChange: onModelChangeProp,
  cartCount = 0
}: AppHeaderProps) {
  const router = useRouter();
  const { user, logout, initializing } = useAuth(requireAuth);
  const { models, defaultModel, selectedModel, setSelectedModel } = useModel();
  const effectiveSelectedModel = selectedModelProp ?? selectedModel;
  const onModelChange = onModelChangeProp ?? setSelectedModel;

  useEffect(() => {
    if (!showModelSelector || !onModelChange) return
    if (!models?.length) return
    const selected = models.find((m) => m.id === effectiveSelectedModel)
    if (selected && selected.enabled !== false) return
    const fallback = models.find((m) => m.enabled !== false)?.id || defaultModel || ''
    if (effectiveSelectedModel !== fallback) onModelChange(fallback)
  }, [defaultModel, effectiveSelectedModel, models, onModelChange, showModelSelector])

  const headerStyle: React.CSSProperties = {
    background: 'rgba(15, 23, 42, 0.8)',
    backdropFilter: 'blur(12px)',
    borderBottom: '1px solid rgba(139, 92, 246, 0.3)',
    position: 'sticky',
    top: 0,
    zIndex: 50,
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)'
  };

  if (requireAuth && (initializing || !user)) {
    return (
      <header style={headerStyle}>
        <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '16px 40px' }}>
          <div style={{ fontSize: '14px', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '16px', height: '16px', border: '2px solid #8b5cf6', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
            Initializing...
          </div>
        </div>
        <style jsx>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </header>
    );
  }

  return (
    <header style={headerStyle}>
      <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '16px 40px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div 
          style={{ display: 'flex', alignItems: 'center', gap: '16px', cursor: 'pointer' }}
          onClick={() => router.push('/')}
        >
          <div style={{ 
            width: '40px', 
            height: '40px', 
            background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)', 
            borderRadius: '10px', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            boxShadow: '0 0 15px rgba(99, 102, 241, 0.4)'
          }}>
            <Coffee style={{ width: '24px', height: '24px', color: 'white' }} />
          </div>
          <span style={{ 
            fontSize: '22px', 
            fontWeight: '800', 
            background: 'linear-gradient(135deg, #ffffff 0%, #c7d2fe 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            letterSpacing: '-0.5px'
          }}>
            {appName}
          </span>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          {showModelSelector && onModelChange && (
            <div style={{ position: 'relative' }}>
              <ModelSelector
                value={effectiveSelectedModel}
                onChange={onModelChange}
                models={models}
                defaultModel={defaultModel}
                style={{
                  padding: '10px 18px',
                  border: '1px solid rgba(139, 92, 246, 0.4)',
                  borderRadius: '12px',
                  background: 'rgba(30, 41, 59, 0.6)',
                  fontSize: '14px',
                  outline: 'none',
                  color: 'white',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  boxShadow: '0 2px 10px rgba(0,0,0,0.2)'
                }}
              />
            </div>
          )}

          {showCart && (
            <div style={{ 
              position: 'relative', 
              cursor: 'pointer',
              padding: '10px',
              background: 'rgba(30, 41, 59, 0.6)',
              borderRadius: '12px',
              border: '1px solid rgba(139, 92, 246, 0.2)',
              transition: 'all 0.2s ease'
            }}>
              <ShoppingCart style={{ width: '22px', height: '22px', color: '#c7d2fe' }} />
              {cartCount > 0 && (
                <span style={{ 
                  position: 'absolute', 
                  top: '-5px', 
                  right: '-5px', 
                  background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)', 
                  color: 'white', 
                  fontSize: '11px', 
                  fontWeight: 'bold',
                  borderRadius: '50%', 
                  width: '20px', 
                  height: '20px', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  boxShadow: '0 2px 8px rgba(239, 68, 68, 0.4)',
                  border: '2px solid #0f172a'
                }}>
                  {cartCount}
                </span>
              )}
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', paddingLeft: '24px', borderLeft: '1px solid rgba(139, 92, 246, 0.2)' }}>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '10px', 
              padding: '8px 16px', 
              background: 'rgba(30, 41, 59, 0.6)', 
              borderRadius: '12px',
              border: '1px solid rgba(139, 92, 246, 0.1)'
            }}>
              <User style={{ width: '18px', height: '18px', color: '#8b5cf6' }} />
              <span style={{ fontSize: '14px', fontWeight: '600', color: '#e2e8f0' }}>
                {initializing ? '...' : (user?.username || user?.email || 'Guest')}
              </span>
            </div>
            
            {user ? (
              <button
                onClick={logout}
                style={{ 
                  padding: '10px 18px', 
                  background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)', 
                  color: 'white', 
                  border: 'none', 
                  borderRadius: '12px', 
                  fontSize: '14px', 
                  fontWeight: '700', 
                  cursor: 'pointer', 
                  transition: 'all 0.2s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: '0 4px 12px rgba(239, 68, 68, 0.3)'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-1px)';
                  e.currentTarget.style.boxShadow = '0 6px 15px rgba(239, 68, 68, 0.4)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = '0 4px 12px rgba(239, 68, 68, 0.3)';
                }}
              >
                <LogOut style={{ width: '16px', height: '16px' }} />
                Logout
              </button>
            ) : (
              !requireAuth && (
                <button
                  onClick={() => router.push('/')}
                  style={{ 
                    padding: '10px 18px', 
                    background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)', 
                    color: 'white', 
                    border: 'none', 
                    borderRadius: '12px', 
                    fontSize: '14px', 
                    fontWeight: '700', 
                    cursor: 'pointer', 
                    transition: 'all 0.2s ease',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-1px)';
                    e.currentTarget.style.boxShadow = '0 6px 15px rgba(99, 102, 241, 0.4)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(99, 102, 241, 0.3)';
                  }}
                >
                  <LogIn style={{ width: '16px', height: '16px' }} />
                  Login
                </button>
              )
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
