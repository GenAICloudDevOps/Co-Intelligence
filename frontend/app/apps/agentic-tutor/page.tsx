'use client'

import { useAuth } from '@/app/hooks/useAuth'
import AppHeader from '@/app/components/AppHeader'
import Card from '@/app/components/Card'
import { useState, useEffect, useRef } from 'react'
import { DEFAULT_MODEL } from '@/app/config/models'
import { api } from '@/app/services/api'
import type { Message } from '@/app/types'

interface Topic {
  id: number
  name: string
  category: string
  difficulty: string
  description: string
}

interface TutorMessage extends Message {
  agent_type?: string
}

interface Progress {
  topic: string
  assessments_taken: number
  average_score: number
  completed: boolean
}

export default function AgenticTutor() {
  const { user, loading } = useAuth(true)
  const [topics, setTopics] = useState<Topic[]>([])
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null)
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [messages, setMessages] = useState<TutorMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState('All')
  const [selectedModel, setSelectedModel] = useState(DEFAULT_MODEL)
  const [progress, setProgress] = useState<Progress[]>([])
  const [showProgress, setShowProgress] = useState(false)
  const [currentAgent, setCurrentAgent] = useState<string>('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (user) {
      fetchTopics()
      fetchProgress()
    }
  }, [user])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const fetchTopics = async () => {
    const data = await api.get<Topic[]>('/api/apps/agentic-tutor/topics')
    setTopics(data)
  }

  const fetchProgress = async () => {
    try {
      const data = await api.get<Progress[]>('/api/apps/agentic-tutor/progress')
      setProgress(data)
    } catch (e) {
      console.error('Error fetching progress:', e)
    }
  }

  const startSession = async (topic: Topic) => {
    setSelectedTopic(topic)
    const data = await api.post<{id: number}>('/api/apps/agentic-tutor/sessions', { topic_id: topic.id })
    setSessionId(data.id)
    setCurrentAgent('tutor')
    setMessages([{
      role: 'assistant',
      content: `Welcome! I'm your AI tutor for **${topic.name}**.\n\n🎯 **Quick Actions:**\n• Say "teach me" for a lesson\n• Say "quiz me" for a quiz\n• Say "show progress" to see your stats\n\nWhat would you like to do?`,
      agent_type: 'tutor'
    }])
  }

  const sendMessage = async () => {
    if (!input.trim() || !selectedTopic) return

    const userMsg = { role: 'user', content: input }
    setMessages(prev => [...prev, userMsg])
    const currentInput = input
    setInput('')
    setSending(true)

    try {
      const data = await api.post<{session_id: number, agent_type: string, response: string}>('/api/apps/agentic-tutor/chat', {
        session_id: sessionId,
        topic_id: selectedTopic.id,
        message: currentInput,
        model: selectedModel
      })
      
      setSessionId(data.session_id)
      setCurrentAgent(data.agent_type || 'tutor')
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        agent_type: data.agent_type
      }])
      
      if (data.agent_type === 'grader' || currentInput.toLowerCase().includes('progress')) {
        await fetchProgress()
      }
    } catch (error) {
      console.error('Error:', error)
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' }])
    }
    setSending(false)
  }

  const quickAction = (action: string) => {
    setInput(action)
    setTimeout(() => sendMessage(), 100)
  }

  const getAgentIcon = (agent: string) => {
    const icons: {[key: string]: string} = {
      tutor: '👨‍🏫', assessor: '📝', grader: '✅', hint: '💡', progress: '📊'
    }
    return icons[agent] || '🤖'
  }

  const getAgentColor = (agent: string) => {
    const colors: {[key: string]: string} = {
      tutor: '#f59e0b', assessor: '#10b981', grader: '#8b5cf6', hint: '#3b82f6', progress: '#ec4899'
    }
    return colors[agent] || '#6b7280'
  }

  const categories = ['All', ...Array.from(new Set(topics.map(t => t.category)))]
  const filteredTopics = selectedCategory === 'All' ? topics : topics.filter(t => t.category === selectedCategory)
  const topicProgress = selectedTopic ? progress.find(p => p.topic === selectedTopic.name) : null

  if (loading) return <div style={{ minHeight: '100vh', background: '#0f172a', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}>Loading...</div>

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a' }}>
      <AppHeader appName="Agentic Tutor" showModelSelector={true} selectedModel={selectedModel} onModelChange={setSelectedModel} />
      
      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '24px' }}>
        {!selectedTopic ? (
          <>
            <Card padding="lg">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                <div>
                  <h1 style={{ fontSize: '2rem', marginBottom: '8px', color: 'white' }}>👨‍🏫 Choose a Topic to Learn</h1>
                  <p style={{ color: '#94a3b8' }}>Select a topic to start learning with your AI tutor</p>
                </div>
                <button onClick={() => setShowProgress(!showProgress)} style={{ padding: '10px 20px', background: '#8b5cf6', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: '600' }}>
                  📊 {showProgress ? 'Hide' : 'View'} Progress
                </button>
              </div>
              
              {showProgress && (
                <div style={{ marginBottom: '24px', padding: '20px', background: '#1e293b', borderRadius: '12px' }}>
                  <h3 style={{ color: 'white', marginBottom: '16px' }}>Your Learning Progress</h3>
                  {progress.length === 0 ? (
                    <p style={{ color: '#94a3b8' }}>No progress yet. Start learning to track your progress!</p>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
                      {progress.map((p, i) => (
                        <div key={i} style={{ padding: '16px', background: '#0f172a', borderRadius: '8px', border: '1px solid #334155' }}>
                          <div style={{ fontWeight: '600', color: 'white', marginBottom: '8px' }}>{p.topic}</div>
                          <div style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Quizzes: {p.assessments_taken}</div>
                          <div style={{ fontSize: '0.85rem', color: p.average_score >= 70 ? '#10b981' : '#f59e0b' }}>
                            Avg Score: {p.average_score.toFixed(0)}%
                          </div>
                          {p.completed && <div style={{ marginTop: '8px', color: '#10b981', fontWeight: '600' }}>✅ Completed</div>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
              
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                {categories.map(cat => (
                  <button key={cat} onClick={() => setSelectedCategory(cat)}
                    style={{ padding: '8px 16px', background: selectedCategory === cat ? '#f59e0b' : '#334155', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: '600' }}>
                    {cat}
                  </button>
                ))}
              </div>
            </Card>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px', marginTop: '24px' }}>
              {filteredTopics.map(topic => {
                const tp = progress.find(p => p.topic === topic.name)
                return (
                  <Card key={topic.id} hover padding="lg">
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                      <span style={{ padding: '4px 12px', background: topic.difficulty === 'beginner' ? '#10b981' : topic.difficulty === 'intermediate' ? '#f59e0b' : '#ef4444', color: 'white', borderRadius: '12px', fontSize: '0.75rem', fontWeight: '600' }}>
                        {topic.difficulty}
                      </span>
                      {tp && <span style={{ fontSize: '0.75rem', color: '#10b981' }}>📊 {tp.average_score.toFixed(0)}%</span>}
                    </div>
                    <h3 style={{ fontSize: '1.25rem', marginBottom: '8px', color: 'white' }}>{topic.name}</h3>
                    <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '8px' }}>{topic.category}</p>
                    <p style={{ color: '#64748b', fontSize: '0.85rem', marginBottom: '16px' }}>{topic.description}</p>
                    <button onClick={() => startSession(topic)} style={{ width: '100%', padding: '10px', background: '#f59e0b', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: '600' }}>
                      {tp ? 'Continue Learning' : 'Start Learning'}
                    </button>
                  </Card>
                )
              })}
            </div>
          </>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '24px' }}>
            <Card padding="lg">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <div>
                  <h2 style={{ fontSize: '1.5rem', color: 'white' }}>{selectedTopic.name}</h2>
                  <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>{selectedTopic.category}</p>
                </div>
                <button onClick={() => { setSelectedTopic(null); setMessages([]); setSessionId(null); }}
                  style={{ padding: '8px 16px', background: '#334155', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>
                  ← Back
                </button>
              </div>

              {/* Agent Status */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', padding: '8px 12px', background: '#1e293b', borderRadius: '8px' }}>
                <span style={{ fontSize: '1.2rem' }}>{getAgentIcon(currentAgent)}</span>
                <span style={{ color: getAgentColor(currentAgent), fontWeight: '600', textTransform: 'capitalize' }}>{currentAgent} Agent</span>
                {sending && <span style={{ marginLeft: 'auto', color: '#94a3b8', fontSize: '0.85rem' }}>Thinking...</span>}
              </div>

              <div style={{ height: '450px', overflowY: 'auto', marginBottom: '16px', padding: '16px', background: '#1e293b', borderRadius: '8px' }}>
                {messages.map((msg, idx) => (
                  <div key={idx} style={{ marginBottom: '16px', padding: '12px', background: msg.role === 'user' ? '#3b82f6' : '#0f172a', borderRadius: '8px', marginLeft: msg.role === 'user' ? '20%' : '0', marginRight: msg.role === 'user' ? '0' : '20%', border: msg.role === 'assistant' ? `2px solid ${getAgentColor(msg.agent_type || 'tutor')}` : 'none' }}>
                    {msg.role === 'assistant' && (
                      <div style={{ fontSize: '0.75rem', color: getAgentColor(msg.agent_type || 'tutor'), marginBottom: '6px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        {getAgentIcon(msg.agent_type || 'tutor')} {msg.agent_type || 'tutor'} agent
                      </div>
                    )}
                    <div style={{ whiteSpace: 'pre-wrap', color: 'white', lineHeight: '1.6' }}>{msg.content}</div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>

              <div style={{ display: 'flex', gap: '8px' }}>
                <input type="text" value={input} onChange={(e) => setInput(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && !sending && sendMessage()}
                  placeholder="Ask a question or type a command..." disabled={sending}
                  style={{ flex: 1, padding: '12px', border: '1px solid #334155', borderRadius: '8px', fontSize: '1rem', background: '#0f172a', color: 'white' }} />
                <button onClick={sendMessage} disabled={sending || !input.trim()}
                  style={{ padding: '12px 24px', background: sending ? '#475569' : '#f59e0b', color: 'white', border: 'none', borderRadius: '8px', cursor: sending ? 'not-allowed' : 'pointer', fontWeight: '600' }}>
                  {sending ? '...' : 'Send'}
                </button>
              </div>
            </Card>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <Card padding="md">
                <h3 style={{ fontSize: '1.1rem', marginBottom: '12px', color: 'white' }}>Quick Actions</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <button onClick={() => quickAction('Give me a quiz on this topic')} style={{ padding: '12px', background: '#10b981', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', textAlign: 'left', fontWeight: '500' }}>
                    📝 Take a Quiz
                  </button>
                  <button onClick={() => quickAction('Teach me the basics of this topic')} style={{ padding: '12px', background: '#3b82f6', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', textAlign: 'left', fontWeight: '500' }}>
                    📖 Teach Me
                  </button>
                  <button onClick={() => quickAction('Give me a hint')} style={{ padding: '12px', background: '#f59e0b', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', textAlign: 'left', fontWeight: '500' }}>
                    💡 Get a Hint
                  </button>
                  <button onClick={() => quickAction('Show my progress for this topic')} style={{ padding: '12px', background: '#8b5cf6', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', textAlign: 'left', fontWeight: '500' }}>
                    📊 View Progress
                  </button>
                </div>
              </Card>

              {topicProgress && (
                <Card padding="md">
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '12px', color: 'white' }}>Your Progress</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#94a3b8' }}>Quizzes Taken</span>
                      <span style={{ color: 'white', fontWeight: '600' }}>{topicProgress.assessments_taken}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#94a3b8' }}>Average Score</span>
                      <span style={{ color: topicProgress.average_score >= 70 ? '#10b981' : '#f59e0b', fontWeight: '600' }}>{topicProgress.average_score.toFixed(0)}%</span>
                    </div>
                    <div style={{ marginTop: '8px', height: '8px', background: '#334155', borderRadius: '4px', overflow: 'hidden' }}>
                      <div style={{ width: `${topicProgress.average_score}%`, height: '100%', background: topicProgress.average_score >= 70 ? '#10b981' : '#f59e0b' }}></div>
                    </div>
                  </div>
                </Card>
              )}

              <Card padding="md">
                <h3 style={{ fontSize: '1.1rem', marginBottom: '8px', color: 'white' }}>Agent Flow</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.8rem' }}>
                  {['tutor', 'assessor', 'grader', 'hint', 'progress'].map(agent => (
                    <div key={agent} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', background: currentAgent === agent ? '#1e293b' : 'transparent', borderRadius: '6px', border: currentAgent === agent ? `1px solid ${getAgentColor(agent)}` : '1px solid transparent' }}>
                      <span>{getAgentIcon(agent)}</span>
                      <span style={{ color: currentAgent === agent ? getAgentColor(agent) : '#64748b', textTransform: 'capitalize' }}>{agent}</span>
                      {currentAgent === agent && <span style={{ marginLeft: 'auto', color: getAgentColor(agent) }}>●</span>}
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
