'use client'

import { useState, useEffect } from 'react'
import AppHeader from '../../design-system/components/AppHeader'
import Card from '../../design-system/components/Card'
import Button from '../../design-system/components/Button'
import { ModelSelector } from '../../config/models'
import { useModel } from '../../components/ModelProvider'
import { api } from '../../services/api'
import { useSpeechToText } from '../../hooks/useSpeechToText'

interface Course {
  id: number
  title: string
  description: string
  category: string
  difficulty: string
  duration_hours: number
}

interface Enrollment {
  id: number
  course: Course
  enrolled_at: string
  progress: number
  completed: boolean
}

const SUBTOPICS = [
  { id: 1, name: 'Introduction & Overview', icon: '📖' },
  { id: 2, name: 'Core Concepts', icon: '🎯' },
  { id: 3, name: 'Hands-on Practice', icon: '💻' },
  { id: 4, name: 'Advanced Topics', icon: '🚀' },
  { id: 5, name: 'Review & Assessment', icon: '✅' },
]

export default function AgenticLMS() {
  const { models, defaultModel, selectedModel, setSelectedModel } = useModel()
  const [view, setView] = useState<'home' | 'catalog' | 'enrollments'>('home')
  const [courses, setCourses] = useState<Course[]>([])
  const [enrollments, setEnrollments] = useState<Enrollment[]>([])
  const [chatOpen, setChatOpen] = useState(false)
  const [chatMessage, setChatMessage] = useState('')
  const [chatHistory, setChatHistory] = useState<{role: string, content: string}[]>([])
  const [loading, setLoading] = useState(false)
  const [completedSubtopics, setCompletedSubtopics] = useState<{[enrollmentId: number]: number[]}>({})
  const [expandedEnrollment, setExpandedEnrollment] = useState<number | null>(null)
  const { isSupported: voiceSupported, isListening, toggle: toggleSpeechToText } = useSpeechToText({
    onTranscript: (text) => setChatMessage(text),
  })

  useEffect(() => {
    fetchCourses()
    fetchEnrollments()
    const saved = localStorage.getItem('lms_progress')
    if (saved) setCompletedSubtopics(JSON.parse(saved))
  }, [])

  const fetchCourses = async () => {
    try {
      const data = await api.get<Course[]>('/api/apps/agentic-lms/courses')
      setCourses(data)
    } catch (error) {
      console.error('Error fetching courses:', error)
    }
  }

  const fetchEnrollments = async () => {
    try {
      const data = await api.get<Enrollment[]>('/api/apps/agentic-lms/enrollments')
      setEnrollments(data)
    } catch (error) {
      console.error('Error fetching enrollments:', error)
    }
  }

  const handleEnroll = async (courseId: number) => {
    try {
      await api.post(`/api/apps/agentic-lms/enrollments/${courseId}`, {})
      await fetchEnrollments()
      alert('Successfully enrolled!')
    } catch (error: any) {
      alert(error.message || 'Enrollment failed')
    }
  }

  const toggleSubtopic = (enrollmentId: number, subtopicId: number) => {
    setCompletedSubtopics(prev => {
      const current = prev[enrollmentId] || []
      const updated = current.includes(subtopicId)
        ? current.filter(id => id !== subtopicId)
        : [...current, subtopicId]
      const newState = { ...prev, [enrollmentId]: updated }
      localStorage.setItem('lms_progress', JSON.stringify(newState))
      return newState
    })
  }

  const getProgress = (enrollmentId: number) => {
    const completed = completedSubtopics[enrollmentId] || []
    return Math.round((completed.length / SUBTOPICS.length) * 100)
  }

  const handleChat = async () => {
    if (!chatMessage.trim()) return
    setLoading(true)
    setChatHistory([...chatHistory, { role: 'user', content: chatMessage }])
    
    try {
      const data = await api.post<{response: string}>('/api/apps/agentic-lms/chat', {
        message: chatMessage,
        model: selectedModel
      })
      setChatHistory(prev => [...prev, { role: 'assistant', content: data.response }])
      setChatMessage('')
      if (data.response.includes('enrolled')) await fetchEnrollments()
    } catch (error: any) {
      console.error('Chat error:', error)
      const errorMessage = error?.message || 'API call failed'
      setChatHistory(prev => [...prev, { role: 'assistant', content: `❌ ${errorMessage}` }])
    } finally {
      setLoading(false)
    }
  }

  const isEnrolled = (courseId: number) => enrollments.some(e => e.course.id === courseId)
  const featuredCourses = courses.slice(0, 4)

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0a0f1e 0%, #1a1042 100%)', color: 'white' }}>
      <AppHeader appName="Agentic LMS" />

      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '40px' }}>
        <div style={{ display: 'flex', gap: '20px', marginBottom: '40px', borderBottom: '1px solid rgba(139, 92, 246, 0.3)', paddingBottom: '20px', alignItems: 'center' }}>
          <Button variant={view === 'home' ? 'primary' : 'secondary'} size="sm" onClick={() => setView('home')}>🏠 Home</Button>
          <Button variant={view === 'catalog' ? 'primary' : 'secondary'} size="sm" onClick={() => setView('catalog')}>📚 Course Catalog</Button>
          <Button variant={view === 'enrollments' ? 'primary' : 'secondary'} size="sm" onClick={() => setView('enrollments')}>📖 My Enrollments</Button>
          <div style={{ marginLeft: 'auto' }}>
            <ModelSelector value={selectedModel} onChange={setSelectedModel} models={models} defaultModel={defaultModel} />
          </div>
        </div>

        {view === 'home' && (
          <div>
            <div style={{ textAlign: 'center', marginBottom: '60px' }}>
              <h1 style={{ fontSize: '3rem', fontWeight: 'bold', marginBottom: '16px' }}>Learning Management System</h1>
              <p style={{ fontSize: '1.2rem', color: '#94a3b8' }}>AI-Powered Course Discovery & Learning</p>
            </div>
            <h2 style={{ fontSize: '1.8rem', marginBottom: '30px', fontWeight: 'bold' }}>Featured Courses</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px' }}>
              {featuredCourses.map(course => (
                <Card key={course.id} padding="lg" hover>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                    <span style={{ padding: '4px 12px', background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)', borderRadius: '12px', fontSize: '0.75rem', fontWeight: '700' }}>{course.category}</span>
                    <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>{course.difficulty}</span>
                  </div>
                  <h3 style={{ fontSize: '1.4rem', fontWeight: '800', marginBottom: '12px', background: 'linear-gradient(135deg, #ffffff 0%, #c7d2fe 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>{course.title}</h3>
                  <p style={{ color: '#cbd5e1', fontSize: '0.95rem', marginBottom: '20px', lineHeight: '1.6' }}>{course.description}</p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.9rem', color: '#a5b4fc', fontWeight: '600' }}>⏱️ {course.duration_hours}h</span>
                    {isEnrolled(course.id) ? (
                      <span style={{ padding: '8px 16px', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid #10b981', borderRadius: '8px', color: '#10b981', fontWeight: '700' }}>✓ Enrolled</span>
                    ) : (
                      <Button variant="primary" size="sm" onClick={() => handleEnroll(course.id)}>Enroll Now</Button>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          </div>
        )}

        {view === 'catalog' && (
          <div>
            <h2 style={{ fontSize: '2rem', marginBottom: '30px', fontWeight: 'bold' }}>All Courses</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px' }}>
              {courses.map(course => (
                <Card key={course.id} padding="lg" hover>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                    <span style={{ padding: '4px 12px', background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)', borderRadius: '12px', fontSize: '0.75rem', fontWeight: '700' }}>{course.category}</span>
                    <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>{course.difficulty}</span>
                  </div>
                  <h3 style={{ fontSize: '1.4rem', fontWeight: '800', marginBottom: '12px', background: 'linear-gradient(135deg, #ffffff 0%, #c7d2fe 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>{course.title}</h3>
                  <p style={{ color: '#cbd5e1', fontSize: '0.95rem', marginBottom: '20px', lineHeight: '1.6' }}>{course.description}</p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.9rem', color: '#a5b4fc', fontWeight: '600' }}>⏱️ {course.duration_hours}h</span>
                    {isEnrolled(course.id) ? (
                      <span style={{ padding: '8px 16px', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid #10b981', borderRadius: '8px', color: '#10b981', fontWeight: '700' }}>✓ Enrolled</span>
                    ) : (
                      <Button variant="primary" size="sm" onClick={() => handleEnroll(course.id)}>Enroll Now</Button>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          </div>
        )}

        {view === 'enrollments' && (
          <div>
            <h2 style={{ fontSize: '2rem', marginBottom: '30px', fontWeight: 'bold' }}>My Enrollments</h2>
            {enrollments.length === 0 ? (
              <p style={{ color: '#94a3b8', fontSize: '1.1rem' }}>No enrollments yet. Browse the catalog to get started!</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                {enrollments.map(enrollment => {
                  const progress = getProgress(enrollment.id)
                  const completed = completedSubtopics[enrollment.id] || []
                  const isExpanded = expandedEnrollment === enrollment.id
                  
                  return (
                    <div key={enrollment.id} style={{ background: '#1e293b', borderRadius: '12px', border: '1px solid #334155', overflow: 'hidden' }}>
                      <div style={{ padding: '24px', cursor: 'pointer' }} onClick={() => setExpandedEnrollment(isExpanded ? null : enrollment.id)}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '12px' }}>
                          <div>
                            <span style={{ padding: '4px 12px', background: '#6366f1', borderRadius: '12px', fontSize: '0.75rem', fontWeight: '600' }}>{enrollment.course.category}</span>
                            <h3 style={{ fontSize: '1.3rem', fontWeight: 'bold', marginTop: '12px' }}>{enrollment.course.title}</h3>
                          </div>
                          <span style={{ fontSize: '1.5rem' }}>{isExpanded ? '▼' : '▶'}</span>
                        </div>
                        <div style={{ marginTop: '16px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                            <span style={{ fontSize: '0.9rem', color: '#94a3b8' }}>Progress</span>
                            <span style={{ fontSize: '0.9rem', fontWeight: '600', color: progress === 100 ? '#10b981' : '#94a3b8' }}>{progress}%</span>
                          </div>
                          <div style={{ width: '100%', height: '10px', background: '#334155', borderRadius: '5px', overflow: 'hidden' }}>
                            <div style={{ width: `${progress}%`, height: '100%', background: progress === 100 ? '#10b981' : '#6366f1', transition: 'width 0.3s' }}></div>
                          </div>
                        </div>
                      </div>
                      
                      {isExpanded && (
                        <div style={{ padding: '0 24px 24px', borderTop: '1px solid #334155', paddingTop: '20px' }}>
                          <h4 style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '16px', color: '#94a3b8' }}>Course Modules</h4>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            {SUBTOPICS.map(subtopic => {
                              const isCompleted = completed.includes(subtopic.id)
                              return (
                                <label key={subtopic.id} style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 16px', background: isCompleted ? '#10b98120' : '#0f172a', borderRadius: '8px', cursor: 'pointer', border: `1px solid ${isCompleted ? '#10b981' : '#334155'}` }}>
                                  <input
                                    type="checkbox"
                                    checked={isCompleted}
                                    onChange={() => toggleSubtopic(enrollment.id, subtopic.id)}
                                    style={{ width: '20px', height: '20px', accentColor: '#10b981' }}
                                  />
                                  <span style={{ fontSize: '1.2rem' }}>{subtopic.icon}</span>
                                  <span style={{ fontSize: '0.95rem', color: isCompleted ? '#10b981' : 'white' }}>{subtopic.name}</span>
                                  {isCompleted && <span style={{ marginLeft: 'auto', color: '#10b981' }}>✓</span>}
                                </label>
                              )
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Chat Button */}
      <button onClick={() => setChatOpen(!chatOpen)} style={{ position: 'fixed', bottom: '24px', right: '24px', width: '60px', height: '60px', borderRadius: '50%', background: '#6366f1', border: 'none', color: 'white', fontSize: '1.5rem', cursor: 'pointer', boxShadow: '0 4px 12px rgba(99, 102, 241, 0.4)', zIndex: 1000 }}>
        {chatOpen ? '✕' : '💬'}
      </button>

      {/* Chat Modal */}
      {chatOpen && (
        <div style={{ position: 'fixed', bottom: '100px', right: '24px', width: '380px', height: '500px', background: '#1e293b', borderRadius: '16px', border: '1px solid #334155', display: 'flex', flexDirection: 'column', zIndex: 1000 }}>
          <div style={{ padding: '16px', borderBottom: '1px solid #334155' }}>
            <div style={{ fontWeight: '600' }}>🤖 Course Assistant</div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Ask about courses or say "enroll me in..."</div>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {chatHistory.length === 0 && <p style={{ color: '#64748b', textAlign: 'center', padding: '40px' }}>Ask me about courses!</p>}
            {chatHistory.map((msg, idx) => (
              <div key={idx} style={{ padding: '12px', background: msg.role === 'user' ? '#6366f1' : '#334155', borderRadius: '8px', alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '80%' }}>
                <p style={{ fontSize: '0.9rem', margin: 0 }}>{msg.content}</p>
              </div>
            ))}
            {loading && <div style={{ padding: '12px', background: '#334155', borderRadius: '8px', color: '#94a3b8' }}>Thinking...</div>}
          </div>
	          <div style={{ padding: '12px', borderTop: '1px solid #334155', display: 'flex', gap: '8px' }}>
	            <input value={chatMessage} onChange={(e) => setChatMessage(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && handleChat()}
	              placeholder="Ask about courses..." style={{ flex: 1, padding: '10px', background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', color: 'white', outline: 'none' }} />
	            <button
	              onClick={toggleSpeechToText}
	              disabled={!voiceSupported || loading}
	              title={!voiceSupported ? 'Voice input not supported in this browser' : isListening ? 'Stop voice input' : 'Start voice input'}
	              style={{ padding: '10px 12px', background: isListening ? '#ef4444' : '#334155', border: 'none', borderRadius: '8px', color: 'white', cursor: !voiceSupported || loading ? 'not-allowed' : 'pointer', opacity: !voiceSupported ? 0.5 : 1 }}
	            >
	              🎤
	            </button>
	            <button onClick={handleChat} disabled={loading} style={{ padding: '10px 16px', background: '#6366f1', border: 'none', borderRadius: '8px', color: 'white', cursor: 'pointer' }}>Send</button>
	          </div>
        </div>
      )}
    </div>
  )
}
