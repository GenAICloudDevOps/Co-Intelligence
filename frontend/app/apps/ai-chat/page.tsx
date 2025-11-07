'use client'

import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import jsPDF from 'jspdf'
import AppHeader from '../../components/AppHeader'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Message {
  role: string
  content: string
  timestamp: Date
}

interface Session {
  id: number
  title: string
  created_at: string
}

interface Document {
  id: number
  filename: string
  file_size: number
  file_type: string
}

export default function AIChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [model, setModel] = useState('gemini-2.5-flash-lite')
  const [token, setToken] = useState('')
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [sessions, setSessions] = useState<Session[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [isListening, setIsListening] = useState(false)
  const [showSidebar, setShowSidebar] = useState(true)
  const [showDownload, setShowDownload] = useState(false)
  const [streamingMessage, setStreamingMessage] = useState('')
  const [contextSize, setContextSize] = useState(10)
  const [contextInfo, setContextInfo] = useState({ total: 0, inContext: 0 })
  const [documents, setDocuments] = useState<Document[]>([])
  const [webSearchEnabled, setWebSearchEnabled] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const recognitionRef = useRef<any>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const savedToken = localStorage.getItem('token')
    if (!savedToken) {
      window.location.href = '/'
      return
    }
    setToken(savedToken)
    loadSessions(savedToken)
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if ('webkitSpeechRecognition' in window) {
      recognitionRef.current = new (window as any).webkitSpeechRecognition()
      recognitionRef.current.continuous = false
      recognitionRef.current.interimResults = false
      recognitionRef.current.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript
        setInput(transcript)
        setIsListening(false)
      }
      recognitionRef.current.onerror = () => setIsListening(false)
      recognitionRef.current.onend = () => setIsListening(false)
    }
  }, [])

  const loadSessions = async (authToken: string) => {
    try {
      const response = await axios.get(`${API_URL}/api/apps/ai-chat/sessions`, {
        headers: { Authorization: `Bearer ${authToken}` }
      })
      setSessions(response.data)
    } catch (error: any) {
      console.error('Failed to load sessions:', error)
      // Don't show error to user on initial load - they might not have sessions yet
      if (error.response?.status !== 404) {
        // Only log non-404 errors
        console.warn('Session load error:', error.message)
      }
    }
  }

  const loadSession = async (id: number) => {
    try {
      const response = await axios.get(`${API_URL}/api/apps/ai-chat/sessions/${id}/messages`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setMessages(response.data.map((msg: any) => ({
        ...msg,
        timestamp: new Date(msg.created_at)
      })))
      setSessionId(id)
      loadContextInfo(id)
      loadDocuments(id)
    } catch (error) {
      console.error('Failed to load session:', error)
    }
  }

  const loadDocuments = async (sid: number) => {
    try {
      const response = await axios.get(`${API_URL}/api/apps/ai-chat/sessions/${sid}/documents`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setDocuments(response.data)
    } catch (error) {
      console.error('Failed to load documents:', error)
    }
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file || !sessionId) return

    setIsUploading(true)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('session_id', sessionId.toString())

    try {
      const response = await axios.post(`${API_URL}/api/apps/ai-chat/upload`, formData, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        }
      })
      setDocuments(prev => [...prev, response.data])
    } catch (error: any) {
      console.error('Upload failed:', error)
      alert(error.response?.data?.detail || 'Failed to upload file')
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const deleteDocument = async (docId: number) => {
    try {
      await axios.delete(`${API_URL}/api/apps/ai-chat/documents/${docId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setDocuments(prev => prev.filter(d => d.id !== docId))
    } catch (error) {
      console.error('Failed to delete document:', error)
    }
  }

  const deleteSession = async (id: number) => {
    try {
      await axios.delete(`${API_URL}/api/apps/ai-chat/sessions/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setSessions(sessions.filter(s => s.id !== id))
      if (sessionId === id) {
        setSessionId(null)
        setMessages([])
      }
    } catch (error) {
      console.error('Failed to delete session:', error)
    }
  }

  const loadContextInfo = async (sid: number) => {
    try {
      const response = await axios.get(`${API_URL}/api/apps/ai-chat/sessions/${sid}/context?context_size=${contextSize}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setContextInfo({ total: response.data.total_messages, inContext: response.data.context_messages })
    } catch (error) {
      console.error('Failed to load context info:', error)
    }
  }

  const sendMessage = async () => {
    if (!input.trim() || !token || isLoading) return

    const userMessage: Message = { role: 'user', content: input, timestamp: new Date() }
    setMessages(prev => [...prev, userMessage])
    const userInput = input
    setInput('')
    setIsLoading(true)
    setStreamingMessage('')

    try {
      const response = await fetch(`${API_URL}/api/apps/ai-chat/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: userInput,
          model,
          session_id: sessionId,
          context_size: contextSize,
          web_search: webSearchEnabled
        })
      })

      if (response.status === 401) {
        localStorage.removeItem('token')
        alert('Session expired. Please login again.')
        window.location.href = '/'
        return
      }

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let fullResponse = ''
      let newSessionId = sessionId

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = JSON.parse(line.slice(6))
              if (data.chunk) {
                fullResponse += data.chunk
                setStreamingMessage(fullResponse)
              }
              if (data.session_id) {
                newSessionId = data.session_id
              }
              if (data.done) {
                setMessages(prev => [...prev, {
                  role: 'assistant',
                  content: fullResponse,
                  timestamp: new Date()
                }])
                setStreamingMessage('')
                setSessionId(newSessionId)
                if (!sessionId) loadSessions(token)
                if (newSessionId) loadContextInfo(newSessionId)
              }
            }
          }
        }
      }
    } catch (error: any) {
      console.error('Chat error:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${error.message || 'Failed to get response'}. Please check your connection and try again.`,
        timestamp: new Date()
      }])
      setStreamingMessage('')
    } finally {
      setIsLoading(false)
    }
  }

  const exportToPDF = () => {
    const doc = new jsPDF()
    let y = 20
    doc.setFontSize(16)
    doc.text('Chat Export', 20, y)
    y += 10
    
    messages.forEach(msg => {
      doc.setFontSize(10)
      doc.text(`${msg.role.toUpperCase()}: ${msg.content.substring(0, 100)}`, 20, y)
      y += 10
      if (y > 280) {
        doc.addPage()
        y = 20
      }
    })
    
    doc.save('chat-export.pdf')
    setShowDownload(false)
  }

  const exportToTXT = () => {
    const text = messages.map(msg => 
      `[${msg.timestamp.toLocaleString()}] ${msg.role.toUpperCase()}: ${msg.content}`
    ).join('\n\n')
    
    const blob = new Blob([text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'chat-export.txt'
    a.click()
    setShowDownload(false)
  }

  const toggleVoiceInput = () => {
    if (isListening) {
      recognitionRef.current?.stop()
    } else {
      recognitionRef.current?.start()
      setIsListening(true)
    }
  }

  const speakText = (text: string) => {
    const utterance = new SpeechSynthesisUtterance(text)
    window.speechSynthesis.speak(utterance)
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const filteredMessages = messages.filter(msg => 
    msg.content.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)' }}>
      <AppHeader appName="Co-Intelligence" />
      <div style={{ 
        display: 'flex', 
        minHeight: 'calc(100vh - 73px)',
        color: 'white' 
      }}>
      {/* Sidebar */}
      {showSidebar && (
        <div style={{ 
          width: '300px', 
          background: 'rgba(30, 41, 59, 0.6)',
          backdropFilter: 'blur(10px)',
          borderRight: '1px solid rgba(255, 255, 255, 0.1)',
          padding: '24px', 
          overflowY: 'auto',
          boxShadow: '4px 0 24px rgba(0, 0, 0, 0.3)'
        }}>
          <h2 style={{ marginBottom: '24px', fontSize: '20px', fontWeight: '600' }}>Chat History</h2>
          <button 
            onClick={() => { setSessionId(null); setMessages([]) }}
            style={{ 
              width: '100%', 
              padding: '14px', 
              background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)', 
              border: 'none', 
              borderRadius: '12px', 
              color: 'white', 
              cursor: 'pointer', 
              marginBottom: '20px',
              fontWeight: '600',
              fontSize: '15px',
              boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)',
              transition: 'transform 0.2s'
            }}
            onMouseOver={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
            onMouseOut={(e) => e.currentTarget.style.transform = 'translateY(0)'}
          >
            + New Chat
          </button>
          {sessions.map(session => (
            <div key={session.id} style={{ 
              marginBottom: '12px', 
              background: 'rgba(15, 23, 42, 0.6)', 
              padding: '14px', 
              borderRadius: '12px', 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              border: '1px solid rgba(255, 255, 255, 0.05)',
              transition: 'all 0.2s'
            }}
            onMouseOver={(e) => e.currentTarget.style.background = 'rgba(15, 23, 42, 0.8)'}
            onMouseOut={(e) => e.currentTarget.style.background = 'rgba(15, 23, 42, 0.6)'}
            >
              <div onClick={() => loadSession(session.id)} style={{ cursor: 'pointer', flex: 1 }}>
                <div style={{ fontSize: '14px', fontWeight: '500' }}>{session.title}</div>
                <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>{new Date(session.created_at).toLocaleDateString()}</div>
              </div>
              <button onClick={() => deleteSession(session.id)} style={{ 
                background: 'transparent', 
                border: 'none', 
                color: '#ef4444', 
                cursor: 'pointer', 
                fontSize: '20px',
                padding: '4px 8px',
                borderRadius: '6px',
                transition: 'background 0.2s'
              }}
              onMouseOver={(e) => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)'}
              onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
              >×</button>
            </div>
          ))}
        </div>
      )}

      {/* Main Chat */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '24px' }}>
        {/* Header */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          marginBottom: '24px',
          background: 'rgba(30, 41, 59, 0.6)',
          backdropFilter: 'blur(10px)',
          padding: '16px 24px',
          borderRadius: '16px',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          boxShadow: '0 4px 24px rgba(0, 0, 0, 0.2)'
        }}>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <button onClick={() => setShowSidebar(!showSidebar)} style={{ 
              padding: '10px 14px', 
              background: 'rgba(15, 23, 42, 0.6)', 
              border: '1px solid rgba(255, 255, 255, 0.1)', 
              borderRadius: '10px', 
              color: 'white', 
              cursor: 'pointer',
              fontSize: '18px',
              transition: 'all 0.2s'
            }}
            onMouseOver={(e) => e.currentTarget.style.background = 'rgba(15, 23, 42, 0.9)'}
            onMouseOut={(e) => e.currentTarget.style.background = 'rgba(15, 23, 42, 0.6)'}
            >☰</button>
            <h1 style={{ margin: 0, fontSize: '24px', fontWeight: '600' }}>AI Chat</h1>
          </div>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <button
              onClick={() => setWebSearchEnabled(!webSearchEnabled)}
              style={{
                padding: '10px 16px',
                background: webSearchEnabled ? 'rgba(99, 102, 241, 0.3)' : 'rgba(15, 23, 42, 0.6)',
                border: `1px solid ${webSearchEnabled ? 'rgba(99, 102, 241, 0.5)' : 'rgba(255, 255, 255, 0.1)'}`,
                borderRadius: '10px',
                color: 'white',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: '500',
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
              title={webSearchEnabled ? "Web search enabled - AI will search the internet for current information" : "Web search disabled - Click to enable real-time web search"}
            >
              🌐 Web Search: {webSearchEnabled ? 'ON' : 'OFF'}
            </button>
            <select value={model} onChange={(e) => setModel(e.target.value)} style={{ 
              padding: '10px 16px', 
              background: 'rgba(15, 23, 42, 0.6)', 
              color: 'white', 
              border: '1px solid rgba(255, 255, 255, 0.1)', 
              borderRadius: '10px',
              fontSize: '14px',
              fontWeight: '500',
              cursor: 'pointer'
            }}>
              <optgroup label="Gemini">
                <option value="gemini-2.5-flash-lite">Gemini 2.5 Flash Lite</option>
                <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
                <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
              </optgroup>
              <optgroup label="Groq">
                <option value="groq/compound">Groq Compound</option>
                <option value="meta-llama/llama-4-scout-17b-16e-instruct">Llama 4 Scout</option>
              </optgroup>
              <optgroup label="AWS Bedrock">
                <option value="amazon.nova-lite-v1:0">Amazon Nova Lite</option>
                <option value="amazon.nova-pro-v1:0">Amazon Nova Pro</option>
              </optgroup>
            </select>
            <div style={{ position: 'relative' }}>
              <button 
                onClick={() => setShowDownload(!showDownload)} 
                style={{ 
                  padding: '10px 14px', 
                  background: 'rgba(15, 23, 42, 0.6)', 
                  border: '1px solid rgba(255, 255, 255, 0.1)', 
                  borderRadius: '10px', 
                  color: 'white', 
                  cursor: 'pointer',
                  fontSize: '18px',
                  transition: 'all 0.2s'
                }}
                onMouseOver={(e) => e.currentTarget.style.background = 'rgba(15, 23, 42, 0.9)'}
                onMouseOut={(e) => e.currentTarget.style.background = 'rgba(15, 23, 42, 0.6)'}
              >⬇️</button>
              {showDownload && (
                <div style={{
                  position: 'absolute',
                  top: '50px',
                  right: 0,
                  background: 'rgba(30, 41, 59, 0.95)',
                  backdropFilter: 'blur(10px)',
                  borderRadius: '12px',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
                  overflow: 'hidden',
                  zIndex: 100
                }}>
                  <button onClick={exportToPDF} style={{
                    display: 'block',
                    width: '100%',
                    padding: '12px 24px',
                    background: 'transparent',
                    border: 'none',
                    color: 'white',
                    cursor: 'pointer',
                    textAlign: 'left',
                    fontSize: '14px',
                    transition: 'background 0.2s'
                  }}
                  onMouseOver={(e) => e.currentTarget.style.background = 'rgba(99, 102, 241, 0.2)'}
                  onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
                  >📄 Export as PDF</button>
                  <button onClick={exportToTXT} style={{
                    display: 'block',
                    width: '100%',
                    padding: '12px 24px',
                    background: 'transparent',
                    border: 'none',
                    color: 'white',
                    cursor: 'pointer',
                    textAlign: 'left',
                    fontSize: '14px',
                    transition: 'background 0.2s'
                  }}
                  onMouseOver={(e) => e.currentTarget.style.background = 'rgba(99, 102, 241, 0.2)'}
                  onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
                  >📝 Export as TXT</button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Context Indicator */}
        {sessionId && (
          <div style={{
            background: 'rgba(30, 41, 59, 0.6)',
            backdropFilter: 'blur(10px)',
            padding: '16px 24px',
            borderRadius: '12px',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'center',
            gap: '16px'
          }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '8px' }}>
                Context Memory: {contextInfo.inContext}/{contextInfo.total} messages
              </div>
              <div style={{ 
                height: '8px', 
                background: 'rgba(15, 23, 42, 0.6)', 
                borderRadius: '4px', 
                overflow: 'hidden' 
              }}>
                <div style={{ 
                  height: '100%', 
                  width: `${contextInfo.total > 0 ? (contextInfo.inContext / contextInfo.total) * 100 : 0}%`,
                  background: 'linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%)',
                  transition: 'width 0.3s'
                }}></div>
              </div>
            </div>
            <select 
              value={contextSize} 
              onChange={(e) => setContextSize(Number(e.target.value))}
              style={{
                padding: '8px 12px',
                background: 'rgba(15, 23, 42, 0.6)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '8px',
                color: 'white',
                fontSize: '13px',
                cursor: 'pointer'
              }}
            >
              <option value="5">5 pairs</option>
              <option value="10">10 pairs</option>
              <option value="20">20 pairs</option>
              <option value="50">50 pairs</option>
            </select>
            <button
              onClick={() => { setMessages([]); setContextInfo({ total: 0, inContext: 0 }) }}
              style={{
                padding: '8px 16px',
                background: 'rgba(239, 68, 68, 0.2)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '8px',
                color: '#ef4444',
                fontSize: '13px',
                cursor: 'pointer',
                fontWeight: '500',
                transition: 'all 0.2s'
              }}
              onMouseOver={(e) => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.3)'}
              onMouseOut={(e) => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.2)'}
            >
              Clear Context
            </button>
          </div>
        )}

        {/* Search */}
        <input
          type="text"
          placeholder="🔍 Search messages..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{ 
            padding: '14px 20px', 
            background: 'rgba(30, 41, 59, 0.6)',
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255, 255, 255, 0.1)', 
            borderRadius: '12px', 
            color: 'white', 
            marginBottom: '20px',
            fontSize: '14px'
          }}
        />

        {/* Messages */}
        <div style={{ 
          flex: 1, 
          overflowY: 'auto', 
          background: 'rgba(30, 41, 59, 0.4)',
          backdropFilter: 'blur(10px)',
          padding: '24px', 
          borderRadius: '16px', 
          marginBottom: '20px',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          boxShadow: 'inset 0 2px 12px rgba(0, 0, 0, 0.2)'
        }}>
          {filteredMessages.map((msg, idx) => (
            <div key={idx} style={{ 
              marginBottom: '28px', 
              display: 'flex', 
              flexDirection: msg.role === 'user' ? 'row-reverse' : 'row', 
              gap: '14px',
              animation: 'fadeIn 0.3s ease-in'
            }}>
              <div style={{ 
                width: '44px', 
                height: '44px', 
                borderRadius: '50%', 
                background: msg.role === 'user' 
                  ? 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)' 
                  : 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center', 
                flexShrink: 0,
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
                fontSize: '20px'
              }}>
                {msg.role === 'user' ? '👤' : '🤖'}
              </div>
              <div style={{ flex: 1, maxWidth: '75%' }}>
                <div style={{ 
                  padding: '16px 20px', 
                  borderRadius: '16px', 
                  background: msg.role === 'user' 
                    ? 'rgba(59, 130, 246, 0.15)' 
                    : 'rgba(139, 92, 246, 0.15)',
                  backdropFilter: 'blur(10px)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)'
                }}>
                  <ReactMarkdown
                    components={{
                      code({ node, inline, className, children, ...props }: any) {
                        const match = /language-(\w+)/.exec(className || '')
                        return !inline && match ? (
                          <div style={{ position: 'relative', marginTop: '12px' }}>
                            <button 
                              onClick={() => copyToClipboard(String(children))}
                              style={{ 
                                position: 'absolute', 
                                right: '12px', 
                                top: '12px', 
                                padding: '6px 12px', 
                                background: 'rgba(15, 23, 42, 0.8)', 
                                border: '1px solid rgba(255, 255, 255, 0.1)', 
                                borderRadius: '8px', 
                                color: 'white', 
                                cursor: 'pointer', 
                                fontSize: '12px',
                                fontWeight: '500',
                                transition: 'all 0.2s',
                                zIndex: 10
                              }}
                              onMouseOver={(e) => e.currentTarget.style.background = 'rgba(99, 102, 241, 0.8)'}
                              onMouseOut={(e) => e.currentTarget.style.background = 'rgba(15, 23, 42, 0.8)'}
                            >
                              📋
                            </button>
                            <SyntaxHighlighter style={vscDarkPlus} language={match[1]} PreTag="div" {...props}>
                              {String(children).replace(/\n$/, '')}
                            </SyntaxHighlighter>
                          </div>
                        ) : (
                          <code className={className} {...props} style={{ 
                            background: 'rgba(15, 23, 42, 0.6)', 
                            padding: '3px 8px', 
                            borderRadius: '6px',
                            fontSize: '13px'
                          }}>
                            {children}
                          </code>
                        )
                      }
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                </div>
                <div style={{ display: 'flex', gap: '12px', marginTop: '8px', fontSize: '11px', color: '#94a3b8', alignItems: 'center' }}>
                  <span>{msg.timestamp.toLocaleTimeString()}</span>
                  {msg.role === 'assistant' && (
                    <>
                      <button 
                        onClick={() => copyToClipboard(msg.content)} 
                        style={{ 
                          background: 'transparent', 
                          border: 'none', 
                          color: '#94a3b8', 
                          cursor: 'pointer',
                          fontSize: '16px',
                          padding: '4px',
                          transition: 'color 0.2s'
                        }}
                        onMouseOver={(e) => e.currentTarget.style.color = '#6366f1'}
                        onMouseOut={(e) => e.currentTarget.style.color = '#94a3b8'}
                        title="Copy message"
                      >📋</button>
                      <button 
                        onClick={() => speakText(msg.content)} 
                        style={{ 
                          background: 'transparent', 
                          border: 'none', 
                          color: '#94a3b8', 
                          cursor: 'pointer',
                          fontSize: '16px',
                          padding: '4px',
                          transition: 'color 0.2s'
                        }}
                        onMouseOver={(e) => e.currentTarget.style.color = '#6366f1'}
                        onMouseOut={(e) => e.currentTarget.style.color = '#94a3b8'}
                        title="Speak message"
                      >🔊</button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
          {(isLoading || streamingMessage) && (
            <div style={{ display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
              <div style={{ 
                width: '44px', 
                height: '44px', 
                borderRadius: '50%', 
                background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
                fontSize: '20px'
              }}>🤖</div>
              <div style={{ 
                padding: '16px 20px', 
                borderRadius: '16px', 
                background: 'rgba(139, 92, 246, 0.15)',
                backdropFilter: 'blur(10px)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                flex: 1,
                maxWidth: '75%'
              }}>
                {streamingMessage ? (
                  <ReactMarkdown
                    components={{
                      code({ node, inline, className, children, ...props }: any) {
                        const match = /language-(\w+)/.exec(className || '')
                        return !inline && match ? (
                          <SyntaxHighlighter style={vscDarkPlus} language={match[1]} PreTag="div" {...props}>
                            {String(children).replace(/\n$/, '')}
                          </SyntaxHighlighter>
                        ) : (
                          <code className={className} {...props} style={{ 
                            background: 'rgba(15, 23, 42, 0.6)', 
                            padding: '3px 8px', 
                            borderRadius: '6px',
                            fontSize: '13px'
                          }}>
                            {children}
                          </code>
                        )
                      }
                    }}
                  >
                    {streamingMessage}
                  </ReactMarkdown>
                ) : (
                  <>
                    <span className="typing-indicator">AI is thinking</span>
                    <style jsx>{`
                      .typing-indicator::after {
                        content: '...';
                        animation: dots 1.5s steps(4, end) infinite;
                      }
                      @keyframes dots {
                        0%, 20% { content: '.'; }
                        40% { content: '..'; }
                        60%, 100% { content: '...'; }
                      }
                    `}</style>
                  </>
                )}
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Documents */}
        {documents.length > 0 && (
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '12px' }}>
            {documents.map(doc => (
              <div key={doc.id} style={{
                background: 'rgba(99, 102, 241, 0.2)',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                borderRadius: '8px',
                padding: '8px 12px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '13px'
              }}>
                <span>📎 {doc.filename}</span>
                <span style={{ color: '#94a3b8' }}>({(doc.file_size / 1024).toFixed(1)} KB)</span>
                <button
                  onClick={() => deleteDocument(doc.id)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#ef4444',
                    cursor: 'pointer',
                    fontSize: '16px',
                    padding: '0 4px'
                  }}
                >×</button>
              </div>
            ))}
          </div>
        )}

        {/* Input */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt,.md"
          onChange={handleFileUpload}
          style={{ display: 'none' }}
        />
        <div style={{ 
          display: 'flex', 
          gap: '12px',
          background: 'rgba(30, 41, 59, 0.6)',
          backdropFilter: 'blur(10px)',
          padding: '16px',
          borderRadius: '16px',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          boxShadow: '0 4px 24px rgba(0, 0, 0, 0.2)'
        }}>
          <button 
            onClick={toggleVoiceInput}
            style={{ 
              padding: '14px 16px', 
              background: isListening 
                ? 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)' 
                : 'rgba(15, 23, 42, 0.6)', 
              border: '1px solid rgba(255, 255, 255, 0.1)', 
              borderRadius: '12px', 
              color: 'white', 
              cursor: 'pointer',
              fontSize: '18px',
              transition: 'all 0.2s',
              boxShadow: isListening ? '0 0 20px rgba(239, 68, 68, 0.5)' : 'none'
            }}
          >
            {isListening ? '🔴' : '🎤'}
          </button>
          <button 
            onClick={() => sessionId && fileInputRef.current?.click()}
            disabled={!sessionId || isUploading}
            style={{ 
              padding: '14px 16px', 
              background: isUploading ? 'rgba(100, 116, 139, 0.5)' : 'rgba(15, 23, 42, 0.6)', 
              border: '1px solid rgba(255, 255, 255, 0.1)', 
              borderRadius: '12px', 
              color: !sessionId ? '#64748b' : 'white', 
              cursor: sessionId && !isUploading ? 'pointer' : 'not-allowed',
              fontSize: '18px',
              transition: 'all 0.2s',
              opacity: !sessionId ? 0.5 : 1
            }}
            title={!sessionId ? "Start a chat first to upload documents" : isUploading ? "Uploading..." : "Upload document (PDF, DOCX, TXT, MD)"}
          >
            {isUploading ? '⏳' : '📎'}
          </button>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Type your message..."
            style={{ 
              flex: 1, 
              padding: '14px 20px', 
              background: 'rgba(15, 23, 42, 0.6)', 
              border: '1px solid rgba(255, 255, 255, 0.1)', 
              borderRadius: '12px', 
              color: 'white',
              fontSize: '14px'
            }}
          />
          <button 
            onClick={sendMessage} 
            disabled={isLoading}
            style={{ 
              padding: '14px 32px', 
              background: isLoading 
                ? 'rgba(100, 116, 139, 0.5)' 
                : 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)', 
              border: 'none', 
              borderRadius: '12px', 
              color: 'white', 
              cursor: isLoading ? 'not-allowed' : 'pointer',
              fontWeight: '600',
              fontSize: '15px',
              boxShadow: isLoading ? 'none' : '0 4px 12px rgba(99, 102, 241, 0.3)',
              transition: 'all 0.2s'
            }}
            onMouseOver={(e) => !isLoading && (e.currentTarget.style.transform = 'translateY(-2px)')}
            onMouseOut={(e) => !isLoading && (e.currentTarget.style.transform = 'translateY(0)')}
          >
            Send
          </button>
        </div>
      </div>
      </div>
    </div>
  )
}
