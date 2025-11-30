const API_URL = process.env.NEXT_PUBLIC_API_URL || ''

function getAuthHeaders(): HeadersInit {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function refreshToken(): Promise<boolean> {
  const refresh = localStorage.getItem('refresh_token')
  if (!refresh) return false
  
  try {
    const res = await fetch(`${API_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh })
    })
    if (!res.ok) return false
    
    const data = await res.json()
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    return true
  } catch {
    return false
  }
}

async function fetchWithRefresh<T>(url: string, options: RequestInit): Promise<T> {
  let res = await fetch(url, options)
  
  if (res.status === 401) {
    const refreshed = await refreshToken()
    if (refreshed) {
      // Retry with new token
      const newHeaders = { ...options.headers, ...getAuthHeaders() }
      res = await fetch(url, { ...options, headers: newHeaders })
    } else {
      // Refresh failed, clear and redirect
      localStorage.clear()
      if (typeof window !== 'undefined') window.location.href = '/'
      throw new Error('Session expired')
    }
  }
  
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export const api = {
  async get<T>(endpoint: string): Promise<T> {
    return fetchWithRefresh<T>(`${API_URL}${endpoint}`, {
      headers: { ...getAuthHeaders() }
    })
  },

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    return fetchWithRefresh<T>(`${API_URL}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: data ? JSON.stringify(data) : undefined
    })
  },

  async put<T>(endpoint: string, data: unknown): Promise<T> {
    return fetchWithRefresh<T>(`${API_URL}${endpoint}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(data)
    })
  },

  async delete<T>(endpoint: string): Promise<T> {
    return fetchWithRefresh<T>(`${API_URL}${endpoint}`, {
      method: 'DELETE',
      headers: { ...getAuthHeaders() }
    })
  },

  getStreamUrl(endpoint: string): string {
    return `${API_URL}${endpoint}`
  },

  getAuthHeaders
}
