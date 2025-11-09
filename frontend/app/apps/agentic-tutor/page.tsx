'use client'

import { useAuth } from '@/app/hooks/useAuth'
import AppHeader from '@/app/components/AppHeader'
import Card from '@/app/components/Card'
import { useState, useEffect, useRef } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Topic {
  id: number
  name: string
  category: string
  difficulty: string
  description: string
}

interface Message {
  role: string
  content: string
  agent_type?: string
}

export default function AgenticTutor() {
  const { user, loading } = useAuth(true)
  const [topics, setTopics] = useState<Topic[]>([])
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null)
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState('All')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (user) fetchTopics()
  }, [user])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const fetchTopics = async () => {
    const res = await fetch(`${API_URL}/api/apps/agentic-tutor/topics`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    setTopics(await res.json())
  }

  const startSession = async (topic: Topic) => {
    setSelectedTopic(topic)
    const res = await fetch(`${API_URL}/api/apps/agentic-tutor/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({ topic_id: topic.id })
    })
    const data = await res.json()
    setSessionId(data.id)
    setMessages([{
      role: 'assistant',
      content: `Welcome! I'm your AI tutor for ${topic.name}. Ask me anything, request a quiz, or just say "teach me" to get started!`,
      agent_type: 'tutor'
    }])
  }

  const sendMessage = async () => {
    if (!input.trim() || !selectedTopic) return

    const userMsg = { role: 'user', content: input }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setSending(true)

    try {
      const res = await fetch(`${API_URL}/api/apps/agentic-tutor/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          session_id: sessionId,
          topic_id: selectedTopic.id,
          message: input
        })
      })
      const data = await res.json()
      
      setSessionId(data.session_id)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        agent_type: data.agent_type
      }])
    } catch (error) {
      console.error('Error:', error)
    }
    setSending(false)
  }

  const categories = ['All', ...Array.from(new Set(topics.map(t => t.category)))]
  const filteredTopics = selectedCategory === 'All' 
    ? topics 
    : topics.filter(t => t.category === selectedCategory)

  if (loading) return <div>Loading...</div>

  return (
    <div style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      <AppHeader appName="Agentic Tutor" />
      
      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '24px' }}>
        {!selectedTopic ? (
          <>
            <Card padding="lg">
              <h1 style={{ fontSize: '2rem', marginBottom: '16px', color: 'white' }}>👨‍🏫 Choose a Topic to Learn</h1>
              <p style={{ color: '#94a3b8', marginBottom: '24px' }}>
                Select a topic below to start learning with your AI tutor. You can ask questions, take quizzes, and track your progress.
              </p>
              
              <div style={{ display: 'flex', gap: '12px', marginBottom: '24px', flexWrap: 'wrap' }}>
                {categories.map(cat => (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat)}
                    style={{
                      padding: '8px 16px',
                      background: selectedCategory === cat ? '#f59e0b' : '#e5e7eb',
                      color: selectedCategory === cat ? 'white' : '#374151',
                      border: 'none',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      fontWeight: '600'
                    }}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </Card>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px', marginTop: '24px' }}>
              {filteredTopics.map(topic => (
                <Card key={topic.id} hover padding="lg">
                  <div style={{ marginBottom: '12px' }}>
                    <span style={{
                      padding: '4px 12px',
                      background: topic.difficulty === 'beginner' ? '#10b981' : topic.difficulty === 'intermediate' ? '#f59e0b' : '#ef4444',
                      color: 'white',
                      borderRadius: '12px',
                      fontSize: '0.75rem',
                      fontWeight: '600'
                    }}>
                      {topic.difficulty}
                    </span>
                  </div>
                  <h3 style={{ fontSize: '1.25rem', marginBottom: '8px', color: 'white' }}>{topic.name}</h3>
                  <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '8px' }}>{topic.category}</p>
                  <p style={{ color: '#94a3b8', fontSize: '0.85rem', marginBottom: '16px' }}>{topic.description}</p>
                  <button
                    onClick={() => startSession(topic)}
                    style={{
                      width: '100%',
                      padding: '10px',
                      background: '#f59e0b',
                      color: 'white',
                      border: 'none',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      fontWeight: '600'
                    }}
                  >
                    Start Learning
                  </button>
                </Card>
              ))}
            </div>
          </>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '24px' }}>
            <Card padding="lg">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                <div>
                  <h2 style={{ fontSize: '1.5rem', marginBottom: '4px', color: 'white' }}>{selectedTopic.name}</h2>
                  <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>{selectedTopic.category}</p>
                </div>
                <button
                  onClick={() => { setSelectedTopic(null); setMessages([]); setSessionId(null); }}
                  style={{
                    padding: '8px 16px',
                    background: '#e5e7eb',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: 'pointer'
                  }}
                >
                  ← Back to Topics
                </button>
              </div>

              <div style={{
                height: '500px',
                overflowY: 'auto',
                marginBottom: '16px',
                padding: '16px',
                background: '#f9fafb',
                borderRadius: '8px'
              }}>
                {messages.map((msg, idx) => (
                  <div key={idx} style={{
                    marginBottom: '16px',
                    padding: '12px',
                    background: msg.role === 'user' ? '#dbeafe' : 'white',
                    borderRadius: '8px',
                    marginLeft: msg.role === 'user' ? '20%' : '0',
                    marginRight: msg.role === 'user' ? '0' : '20%'
                  }}>
                    <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '4px', fontWeight: '600' }}>
                      {msg.role === 'user' ? 'You' : `Tutor ${msg.agent_type ? `(${msg.agent_type})` : ''}`}
                    </div>
                    <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>

              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && !sending && sendMessage()}
                  placeholder="Ask a question, request a quiz, or ask for help..."
                  disabled={sending}
                  style={{
                    flex: 1,
                    padding: '12px',
                    border: '1px solid #d1d5db',
                    borderRadius: '8px',
                    fontSize: '1rem'
                  }}
                />
                <button
                  onClick={sendMessage}
                  disabled={sending || !input.trim()}
                  style={{
                    padding: '12px 24px',
                    background: sending ? '#9ca3af' : '#f59e0b',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: sending ? 'not-allowed' : 'pointer',
                    fontWeight: '600'
                  }}
                >
                  {sending ? 'Sending...' : 'Send'}
                </button>
              </div>
            </Card>

            <div>
              <Card padding="md">
                <h3 style={{ fontSize: '1.25rem', marginBottom: '16px', color: 'white' }}>Quick Actions</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <button
                    onClick={() => setInput('Give me a quiz')}
                    style={{
                      padding: '10px',
                      background: '#10b981',
                      color: 'white',
                      border: 'none',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      textAlign: 'left'
                    }}
                  >
                    📝 Take a Quiz
                  </button>
                  <button
                    onClick={() => setInput('I need help with this')}
                    style={{
                      padding: '10px',
                      background: '#3b82f6',
                      color: 'white',
                      border: 'none',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      textAlign: 'left'
                    }}
                  >
                    💡 Get a Hint
                  </button>
                  <button
                    onClick={() => setInput('Show my progress')}
                    style={{
                      padding: '10px',
                      background: '#8b5cf6',
                      color: 'white',
                      border: 'none',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      textAlign: 'left'
                    }}
                  >
                    📊 View Progress
                  </button>
                </div>
              </Card>

              <div style={{ marginTop: '16px' }}>
                <Card padding="md">
                  <h3 style={{ fontSize: '1.25rem', marginBottom: '12px', color: 'white' }}>About This Topic</h3>
                  <p style={{ color: '#94a3b8', fontSize: '0.9rem', lineHeight: '1.6' }}>
                    {selectedTopic.description}
                  </p>
                  <div style={{ marginTop: '12px', padding: '8px', background: '#f3f4f6', borderRadius: '6px' }}>
                    <strong>Difficulty:</strong> {selectedTopic.difficulty}
                  </div>
                </Card>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
