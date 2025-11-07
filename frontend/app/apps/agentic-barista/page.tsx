'use client';

import { useState, useEffect, useRef } from 'react';
import { Send, MessageCircle, Brain, Zap, X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import AppHeader from '../../components/AppHeader';

interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
  agent?: string;
  reasoning?: string;
}

export default function AgenticBarista() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [cart, setCart] = useState<Record<number, number>>({});
  const [totalAmount, setTotalAmount] = useState(0);
  const [selectedModel, setSelectedModel] = useState('gemini-2.5-flash-lite');
  const [isChatOpen, setIsChatOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const id = Math.random().toString(36).substring(7);
    setSessionId(id);
    
    setMessages([{
      id: '1',
      text: "☕ Welcome to Agentic Barista! I'm your AI-powered barista assistant.\n\n🤖 Powered by LangGraph multi-agent workflow:\n• MenuAgent - Browse our menu\n• OrderAgent - Manage your cart\n• ConfirmationAgent - Complete your order\n\nTry:\n• 'Show me the menu'\n• 'Add 2 lattes'\n• 'Show my cart'\n• 'Confirm order'",
      isUser: false,
      timestamp: new Date()
    }]);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!inputText.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputText,
      isUser: true,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/apps/agentic-barista/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: inputText,
          session_id: sessionId,
          model: selectedModel
        })
      });

      const data = await response.json();

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: data.response,
        isUser: false,
        timestamp: new Date(),
        agent: data.agent,
        reasoning: data.reasoning
      };

      setMessages(prev => [...prev, aiMessage]);
      setCart(data.cart || {});
      setTotalAmount(data.total_amount || 0);
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        text: '❌ Sorry, something went wrong. Please try again.',
        isUser: false,
        timestamp: new Date()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const cartItemCount = Object.values(cart).reduce((sum, qty) => sum + qty, 0);

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #faf5f0 0%, #fff8f0 50%, #fff4e6 100%)' }}>
      <AppHeader 
        appName="Coffee and AI" 
        showModelSelector={true}
        showCart={true}
        selectedModel={selectedModel}
        onModelChange={setSelectedModel}
        cartCount={cartItemCount}
      />

      {/* Hero Section */}
      <section style={{ textAlign: 'center', padding: '64px 24px' }}>
        <h1 style={{ fontSize: '48px', fontWeight: 'bold', color: '#292524', marginBottom: '24px', lineHeight: '1.2' }}>
          Where Intelligence Meets Espresso
        </h1>
        <p style={{ fontSize: '20px', color: '#57534e', maxWidth: '768px', margin: '0 auto', lineHeight: '1.6' }}>
          Experience the future of coffee ordering with our AI-powered barista assistant. 
          Get personalized recommendations, smart ordering, and perfect coffee every time.
        </p>
      </section>

      {/* Features Section */}
      <section style={{ maxWidth: '1152px', margin: '0 auto', padding: '48px 24px' }}>
        <h2 style={{ fontSize: '32px', fontWeight: 'bold', textAlign: 'center', color: '#292524', marginBottom: '48px' }}>
          AI-Powered Coffee Experience
        </h2>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '32px' }}>
          {/* Smart Recommendations */}
          <div style={{ background: 'white', borderRadius: '16px', padding: '32px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', border: '1px solid #e7e5e4', textAlign: 'center' }}>
            <div style={{ width: '64px', height: '64px', background: '#dbeafe', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
              <Brain style={{ width: '32px', height: '32px', color: '#2563eb' }} />
            </div>
            <h3 style={{ fontSize: '20px', fontWeight: 'bold', color: '#292524', marginBottom: '12px' }}>Smart Recommendations</h3>
            <p style={{ color: '#57534e', lineHeight: '1.6' }}>
              Our AI learns your preferences and suggests the perfect coffee for your mood and taste.
            </p>
          </div>

          {/* Natural Conversations */}
          <div style={{ background: 'white', borderRadius: '16px', padding: '32px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', border: '1px solid #e7e5e4', textAlign: 'center' }}>
            <div style={{ width: '64px', height: '64px', background: '#dcfce7', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
              <MessageCircle style={{ width: '32px', height: '32px', color: '#16a34a' }} />
            </div>
            <h3 style={{ fontSize: '20px', fontWeight: 'bold', color: '#292524', marginBottom: '12px' }}>Natural Conversations</h3>
            <p style={{ color: '#57534e', lineHeight: '1.6' }}>
              Chat naturally with our AI barista using LangChain and LangGraph technology.
            </p>
          </div>

          {/* Instant Ordering */}
          <div style={{ background: 'white', borderRadius: '16px', padding: '32px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', border: '1px solid #e7e5e4', textAlign: 'center' }}>
            <div style={{ width: '64px', height: '64px', background: '#fef3c7', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
              <Zap style={{ width: '32px', height: '32px', color: '#d97706' }} />
            </div>
            <h3 style={{ fontSize: '20px', fontWeight: 'bold', color: '#292524', marginBottom: '12px' }}>Instant Ordering</h3>
            <p style={{ color: '#57534e', lineHeight: '1.6' }}>
              Place orders quickly with intelligent cart management and seamless checkout.
            </p>
          </div>
        </div>
      </section>

      {/* Floating Chat Button */}
      {!isChatOpen && (
        <button
          onClick={() => setIsChatOpen(true)}
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            width: '64px',
            height: '64px',
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #d97706 0%, #ea580c 100%)',
            color: 'white',
            border: 'none',
            boxShadow: '0 8px 16px rgba(217, 119, 6, 0.4)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'transform 0.2s, box-shadow 0.2s',
            zIndex: 1000
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.transform = 'scale(1.1)';
            e.currentTarget.style.boxShadow = '0 12px 24px rgba(217, 119, 6, 0.5)';
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.transform = 'scale(1)';
            e.currentTarget.style.boxShadow = '0 8px 16px rgba(217, 119, 6, 0.4)';
          }}
        >
          <MessageCircle style={{ width: '32px', height: '32px' }} />
        </button>
      )}

      {/* Chat Modal */}
      {isChatOpen && (
        <div style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          width: '400px',
          height: '600px',
          background: 'white',
          borderRadius: '16px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
          display: 'flex',
          flexDirection: 'column',
          zIndex: 1000,
          overflow: 'hidden'
        }}>
          {/* Modal Header */}
          <div style={{ background: 'linear-gradient(90deg, #d97706 0%, #ea580c 100%)', color: 'white', padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '18px', fontWeight: 'bold', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <MessageCircle style={{ width: '20px', height: '20px' }} />
              Chat with AI Barista
            </h3>
            <button
              onClick={() => setIsChatOpen(false)}
              style={{ background: 'transparent', border: 'none', color: 'white', cursor: 'pointer', padding: '4px' }}
            >
              <X style={{ width: '24px', height: '24px' }} />
            </button>
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '16px', background: '#fafaf9' }}>
            {messages.map((message) => (
              <div
                key={message.id}
                style={{ display: 'flex', justifyContent: message.isUser ? 'flex-end' : 'flex-start', marginBottom: '12px' }}
              >
                <div
                  style={{
                    maxWidth: '80%',
                    borderRadius: '12px',
                    padding: '10px 14px',
                    background: message.isUser ? '#d97706' : 'white',
                    color: message.isUser ? 'white' : '#292524',
                    boxShadow: message.isUser ? 'none' : '0 2px 4px rgba(0,0,0,0.1)',
                    border: message.isUser ? 'none' : '1px solid #e7e5e4',
                    fontSize: '14px'
                  }}
                >
                  {!message.isUser && message.agent && (
                    <div style={{ fontSize: '11px', color: '#d97706', fontWeight: '600', marginBottom: '4px' }}>
                      {message.agent.toUpperCase()} AGENT
                    </div>
                  )}
                  {!message.isUser && message.reasoning && (
                    <div style={{ fontSize: '11px', color: '#78716c', fontStyle: 'italic', marginBottom: '8px', padding: '6px', background: '#fef3c7', borderRadius: '4px', border: '1px solid #fde68a' }}>
                      🧠 AI Reasoning: {message.reasoning}
                    </div>
                  )}
                  <div style={{ whiteSpace: 'pre-wrap', fontSize: '13px' }}>
                    <ReactMarkdown>{message.text}</ReactMarkdown>
                  </div>
                  <div style={{ fontSize: '11px', marginTop: '4px', color: message.isUser ? '#fed7aa' : '#78716c' }}>
                    {message.timestamp.toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))}
            {isLoading && (
              <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                <div style={{ background: 'white', borderRadius: '12px', padding: '10px 14px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', border: '1px solid #e7e5e4' }}>
                  <div style={{ display: 'flex', gap: '6px' }}>
                    <div style={{ width: '6px', height: '6px', background: '#d97706', borderRadius: '50%', animation: 'bounce 1s infinite' }}></div>
                    <div style={{ width: '6px', height: '6px', background: '#d97706', borderRadius: '50%', animation: 'bounce 1s infinite 0.15s' }}></div>
                    <div style={{ width: '6px', height: '6px', background: '#d97706', borderRadius: '50%', animation: 'bounce 1s infinite 0.3s' }}></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div style={{ background: 'white', borderTop: '1px solid #e7e5e4', padding: '12px' }}>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your message..."
                style={{ flex: 1, padding: '10px 12px', border: '1px solid #d6d3d1', borderRadius: '8px', fontSize: '13px', outline: 'none' }}
                disabled={isLoading}
              />
              <button
                onClick={sendMessage}
                disabled={isLoading || !inputText.trim()}
                style={{ padding: '10px 16px', background: isLoading || !inputText.trim() ? '#d6d3d1' : '#d97706', color: 'white', borderRadius: '8px', border: 'none', cursor: isLoading || !inputText.trim() ? 'not-allowed' : 'pointer' }}
              >
                <Send style={{ width: '18px', height: '18px' }} />
              </button>
            </div>
            
            {totalAmount > 0 && (
              <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid #e7e5e4', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '13px', color: '#57534e', fontWeight: '500' }}>Cart Total:</span>
                <span style={{ fontSize: '16px', fontWeight: 'bold', color: '#d97706' }}>${totalAmount.toFixed(2)}</span>
              </div>
            )}
          </div>
        </div>
      )}

      <style jsx>{`
        @keyframes bounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-8px); }
        }
      `}</style>
    </div>
  );
}
