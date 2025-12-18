'use client';

import { useEffect } from 'react';
import { Coffee, ShoppingCart } from 'lucide-react';
import { ModelSelector } from '../config/models';
import { useAuth } from '../hooks/useAuth';
import { useModel } from './ModelProvider';
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

  if (requireAuth && (initializing || !user)) {
    return (
      <header style={{ background: 'white', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', borderBottom: '1px solid #e7e5e4' }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '16px 24px' }}>
          <div style={{ fontSize: '14px', color: '#78716c' }}>Loading...</div>
        </div>
      </header>
    );
  }

  return (
    <header style={{ background: 'white', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', borderBottom: '1px solid #e7e5e4' }}>
      <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '16px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Coffee style={{ width: '32px', height: '32px', color: '#92400e' }} />
          <span style={{ fontSize: '24px', fontWeight: 'bold', color: '#292524' }}>{appName}</span>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {showModelSelector && onModelChange && (
            <ModelSelector
              value={effectiveSelectedModel}
              onChange={onModelChange}
              models={models}
              defaultModel={defaultModel}
              style={{
                padding: '8px 16px',
                border: '1px solid #d6d3d1',
                borderRadius: '8px',
                background: 'white',
                fontSize: '14px',
                outline: 'none',
                color: '#292524',
              }}
            />
          )}

          {showCart && (
            <div style={{ position: 'relative' }}>
              <ShoppingCart style={{ width: '24px', height: '24px', color: '#92400e' }} />
              {cartCount > 0 && (
                <span style={{ position: 'absolute', top: '-8px', right: '-8px', background: '#ef4444', color: 'white', fontSize: '12px', borderRadius: '50%', width: '20px', height: '20px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {cartCount}
                </span>
              )}
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', paddingLeft: '16px', borderLeft: '1px solid #e7e5e4' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px', background: '#fafaf9', borderRadius: '8px' }}>
              <span style={{ fontSize: '18px' }}>👤</span>
              <span style={{ fontSize: '14px', fontWeight: '500', color: '#292524' }}>
                {initializing ? 'Loading…' : (user?.username || user?.email || 'Guest')}
              </span>
            </div>
            
            {user ? (
              <button
                onClick={logout}
                style={{ padding: '8px 16px', background: '#ef4444', color: 'white', border: 'none', borderRadius: '8px', fontSize: '14px', fontWeight: '600', cursor: 'pointer', transition: 'background 0.2s' }}
                onMouseOver={(e) => e.currentTarget.style.background = '#dc2626'}
                onMouseOut={(e) => e.currentTarget.style.background = '#ef4444'}
              >
                Logout
              </button>
            ) : (
              !requireAuth && (
                <button
                  onClick={() => router.push('/')}
                  style={{ padding: '8px 16px', background: '#2563eb', color: 'white', border: 'none', borderRadius: '8px', fontSize: '14px', fontWeight: '600', cursor: 'pointer', transition: 'background 0.2s' }}
                  onMouseOver={(e) => e.currentTarget.style.background = '#1d4ed8'}
                  onMouseOut={(e) => e.currentTarget.style.background = '#2563eb'}
                >
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
