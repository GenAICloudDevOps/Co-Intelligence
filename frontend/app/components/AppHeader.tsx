'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Coffee, ShoppingCart } from 'lucide-react';

interface AppHeaderProps {
  appName: string;
  showModelSelector?: boolean;
  showCart?: boolean;
  selectedModel?: string;
  onModelChange?: (model: string) => void;
  cartCount?: number;
}

export default function AppHeader({
  appName,
  showModelSelector = false,
  showCart = false,
  selectedModel = 'gemini-2.5-flash-lite',
  onModelChange,
  cartCount = 0
}: AppHeaderProps) {
  const [user, setUser] = useState<any>(null);
  const router = useRouter();

  const models = [
    { id: 'gemini-2.5-flash-lite', name: 'Gemini 2.5 Flash Lite', provider: 'Google' },
    { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash', provider: 'Google' },
    { id: 'gemini-2.5-pro', name: 'Gemini 2.5 Pro', provider: 'Google' },
    { id: 'groq/compound', name: 'Groq Compound', provider: 'Groq' },
    { id: 'meta-llama/llama-4-scout-17b-16e-instruct', name: 'Llama 4 Scout', provider: 'Groq' },
    { id: 'amazon.nova-lite-v1:0', name: 'Nova Lite', provider: 'AWS Bedrock' },
    { id: 'amazon.nova-pro-v1:0', name: 'Nova Pro', provider: 'AWS Bedrock' },
  ];

  useEffect(() => {
    const token = localStorage.getItem('token');
    const username = localStorage.getItem('username');
    
    if (!token || !username) {
      router.push('/');
      return;
    }

    // Fetch user from backend
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => {
        if (!res.ok) throw new Error('Unauthorized');
        return res.json();
      })
      .then(data => setUser(data))
      .catch(() => {
        localStorage.clear();
        router.push('/');
      });
  }, [router]);

  const handleLogout = () => {
    localStorage.clear();
    router.push('/');
  };

  if (!user) {
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
            <select
              value={selectedModel}
              onChange={(e) => onModelChange(e.target.value)}
              style={{ padding: '8px 16px', border: '1px solid #d6d3d1', borderRadius: '8px', background: 'white', fontSize: '14px', outline: 'none' }}
            >
              {models.map(model => (
                <option key={model.id} value={model.id}>
                  {model.name} ({model.provider})
                </option>
              ))}
            </select>
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
              <span style={{ fontSize: '14px', fontWeight: '500', color: '#292524' }}>{user.username || user.email}</span>
            </div>
            
            <button
              onClick={handleLogout}
              style={{ padding: '8px 16px', background: '#ef4444', color: 'white', border: 'none', borderRadius: '8px', fontSize: '14px', fontWeight: '600', cursor: 'pointer', transition: 'background 0.2s' }}
              onMouseOver={(e) => e.currentTarget.style.background = '#dc2626'}
              onMouseOut={(e) => e.currentTarget.style.background = '#ef4444'}
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
