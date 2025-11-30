export interface Message {
  id?: string | number
  role: string
  content: string
  timestamp?: Date
  agent_type?: string
}

export interface Session {
  id: number
  title?: string
  created_at: string
}

export interface User {
  id: number
  email: string
  username: string
}

export interface Document {
  id: number
  filename: string
  file_size: number
  file_type: string
}
