'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'
import AppHeader from '../../components/AppHeader'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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

export default function AgenticLMS() {
  const [view, setView] = useState<'home' | 'catalog' | 'enrollments'>('home')
  const [courses, setCourses] = useState<Course[]>([])
  const [enrollments, setEnrollments] = useState<Enrollment[]>([])
  const [chatOpen, setChatOpen] = useState(false)
  const [chatMessage, setChatMessage] = useState('')
  const [chatHistory, setChatHistory] = useState<{role: string, content: string}[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchCourses()
    fetchEnrollments()
  }, [])

  const fetchCourses = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`${API_URL}/api/apps/agentic-lms/courses`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setCourses(response.data)
    } catch (error) {
      console.error('Error fetching courses:', error)
    }
  }

  const fetchEnrollments = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`${API_URL}/api/apps/agentic-lms/enrollments`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setEnrollments(response.data)
    } catch (error) {
      console.error('Error fetching enrollments:', error)
    }
  }

  const handleEnroll = async (courseId: number) => {
    try {
      const token = localStorage.getItem('token')
      await axios.post(`${API_URL}/api/apps/agentic-lms/enrollments/${courseId}`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      })
      await fetchEnrollments()
      alert('Successfully enrolled!')
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Enrollment failed')
    }
  }

  const handleChat = async () => {
    if (!chatMessage.trim()) return
    
    setLoading(true)
    setChatHistory([...chatHistory, { role: 'user', content: chatMessage }])
    
    try {
      const token = localStorage.getItem('token')
      const response = await axios.post(`${API_URL}/api/apps/agentic-lms/chat`, {
        message: chatMessage,
        model: 'gemini-2.5-flash-lite'
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      setChatHistory(prev => [...prev, { role: 'assistant', content: response.data.response }])
      setChatMessage('')
      
      // Refresh enrollments if enrollment happened
      if (response.data.response.includes('enrolled')) {
        await fetchEnrollments()
      }
    } catch (error) {
      console.error('Chat error:', error)
    }
    setLoading(false)
  }

  const isEnrolled = (courseId: number) => {
    return enrollments.some(e => e.course.id === courseId)
  }

  const featuredCourses = courses.slice(0, 4)

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a', color: 'white' }}>
      <AppHeader appName="Agentic LMS" />

      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '40px' }}>
        {/* Navigation */}
        <div style={{ display: 'flex', gap: '20px', marginBottom: '40px', borderBottom: '1px solid #334155', paddingBottom: '20px' }}>
          <button onClick={() => setView('home')} style={{ padding: '10px 20px', background: view === 'home' ? '#6366f1' : 'transparent', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontWeight: '600' }}>
            🏠 Home
          </button>
          <button onClick={() => setView('catalog')} style={{ padding: '10px 20px', background: view === 'catalog' ? '#6366f1' : 'transparent', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontWeight: '600' }}>
            📚 Course Catalog
          </button>
          <button onClick={() => setView('enrollments')} style={{ padding: '10px 20px', background: view === 'enrollments' ? '#6366f1' : 'transparent', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontWeight: '600' }}>
            📖 My Enrollments
          </button>
        </div>

        {/* Home View */}
        {view === 'home' && (
          <div>
            <div style={{ textAlign: 'center', marginBottom: '60px' }}>
              <h1 style={{ fontSize: '3rem', fontWeight: 'bold', marginBottom: '16px' }}>Learning Management System</h1>
              <p style={{ fontSize: '1.2rem', color: '#94a3b8', marginBottom: '8px' }}>AI-Powered</p>
              <p style={{ fontSize: '1rem', color: '#64748b' }}>Use natural language to discover and enroll in courses</p>
            </div>

            <h2 style={{ fontSize: '1.8rem', marginBottom: '30px', fontWeight: 'bold' }}>Featured Courses</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px' }}>
              {featuredCourses.map(course => (
                <div key={course.id} style={{ background: '#1e293b', borderRadius: '12px', padding: '24px', border: '1px solid #334155' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '12px' }}>
                    <span style={{ padding: '4px 12px', background: '#6366f1', borderRadius: '12px', fontSize: '0.75rem', fontWeight: '600' }}>{course.category}</span>
                    <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>{course.difficulty}</span>
                  </div>
                  <h3 style={{ fontSize: '1.2rem', fontWeight: 'bold', marginBottom: '12px' }}>{course.title}</h3>
                  <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '16px', lineHeight: '1.6' }}>{course.description}</p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.85rem', color: '#64748b' }}>⏱️ {course.duration_hours}h</span>
                    {isEnrolled(course.id) ? (
                      <span style={{ padding: '8px 16px', background: '#334155', borderRadius: '6px', color: '#10b981', fontWeight: '600', fontSize: '0.9rem' }}>
                        ✓ Enrolled
                      </span>
                    ) : (
                      <button onClick={() => handleEnroll(course.id)} style={{ padding: '8px 16px', background: '#10b981', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontWeight: '600', fontSize: '0.9rem' }}>
                        Enroll Now
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Catalog View */}
        {view === 'catalog' && (
          <div>
            <h2 style={{ fontSize: '2rem', marginBottom: '30px', fontWeight: 'bold' }}>All Courses</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px' }}>
              {courses.map(course => (
                <div key={course.id} style={{ background: '#1e293b', borderRadius: '12px', padding: '24px', border: '1px solid #334155' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '12px' }}>
                    <span style={{ padding: '4px 12px', background: '#6366f1', borderRadius: '12px', fontSize: '0.75rem', fontWeight: '600' }}>{course.category}</span>
                    <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>{course.difficulty}</span>
                  </div>
                  <h3 style={{ fontSize: '1.2rem', fontWeight: 'bold', marginBottom: '12px' }}>{course.title}</h3>
                  <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '16px', lineHeight: '1.6' }}>{course.description}</p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.85rem', color: '#64748b' }}>⏱️ {course.duration_hours}h</span>
                    {isEnrolled(course.id) ? (
                      <span style={{ padding: '8px 16px', background: '#334155', borderRadius: '6px', color: '#10b981', fontWeight: '600', fontSize: '0.9rem' }}>
                        ✓ Enrolled
                      </span>
                    ) : (
                      <button onClick={() => handleEnroll(course.id)} style={{ padding: '8px 16px', background: '#10b981', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontWeight: '600', fontSize: '0.9rem' }}>
                        Enroll Now
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Enrollments View */}
        {view === 'enrollments' && (
          <div>
            <h2 style={{ fontSize: '2rem', marginBottom: '30px', fontWeight: 'bold' }}>My Enrollments</h2>
            {enrollments.length === 0 ? (
              <p style={{ color: '#94a3b8', fontSize: '1.1rem' }}>No enrollments yet. Browse the catalog to get started!</p>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px' }}>
                {enrollments.map(enrollment => (
                  <div key={enrollment.id} style={{ background: '#1e293b', borderRadius: '12px', padding: '24px', border: '1px solid #334155' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '12px' }}>
                      <span style={{ padding: '4px 12px', background: '#6366f1', borderRadius: '12px', fontSize: '0.75rem', fontWeight: '600' }}>{enrollment.course.category}</span>
                      <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>{enrollment.course.difficulty}</span>
                    </div>
                    <h3 style={{ fontSize: '1.2rem', fontWeight: 'bold', marginBottom: '12px' }}>{enrollment.course.title}</h3>
                    <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '16px', lineHeight: '1.6' }}>{enrollment.course.description}</p>
                    <div style={{ marginBottom: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Progress</span>
                        <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>{enrollment.progress}%</span>
                      </div>
                      <div style={{ width: '100%', height: '8px', background: '#334155', borderRadius: '4px', overflow: 'hidden' }}>
                        <div style={{ width: `${enrollment.progress}%`, height: '100%', background: '#10b981', transition: 'width 0.3s' }}></div>
                      </div>
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
                      Enrolled: {new Date(enrollment.enrolled_at).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Chatbot */}
      {chatOpen && (
        <div style={{ position: 'fixed', bottom: '100px', right: '30px', width: '400px', height: '500px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155', display: 'flex', flexDirection: 'column', zIndex: 1000 }}>
          <div style={{ padding: '16px', borderBottom: '1px solid #334155', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 'bold' }}>🤖 Course Assistant</h3>
            <button onClick={() => setChatOpen(false)} style={{ background: 'transparent', border: 'none', color: 'white', cursor: 'pointer', fontSize: '1.2rem' }}>✕</button>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {chatHistory.map((msg, idx) => (
              <div key={idx} style={{ padding: '12px', background: msg.role === 'user' ? '#6366f1' : '#334155', borderRadius: '8px', alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '80%' }}>
                <p style={{ fontSize: '0.9rem', margin: 0 }}>{msg.content}</p>
              </div>
            ))}
          </div>
          <div style={{ padding: '16px', borderTop: '1px solid #334155', display: 'flex', gap: '8px' }}>
            <input 
              value={chatMessage}
              onChange={(e) => setChatMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleChat()}
              placeholder="Ask about courses..."
              style={{ flex: 1, padding: '10px', background: '#0f172a', border: '1px solid #334155', borderRadius: '6px', color: 'white' }}
            />
            <button onClick={handleChat} disabled={loading} style={{ padding: '10px 20px', background: '#6366f1', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontWeight: '600' }}>
              {loading ? '...' : 'Send'}
            </button>
          </div>
        </div>
      )}

      {/* Chat Button */}
      <button onClick={() => setChatOpen(!chatOpen)} style={{ position: 'fixed', bottom: '30px', right: '30px', width: '60px', height: '60px', borderRadius: '50%', background: '#6366f1', border: 'none', color: 'white', fontSize: '1.5rem', cursor: 'pointer', boxShadow: '0 4px 12px rgba(0,0,0,0.3)', zIndex: 999 }}>
        💬
      </button>
    </div>
  )
}
