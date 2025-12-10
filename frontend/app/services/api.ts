const API_URL = process.env.NEXT_PUBLIC_API_URL || ''

async function refreshToken(): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/api/auth/refresh`, {
      method: 'POST',
      credentials: 'include'
    })
    if (!res.ok) return false
    return true
  } catch {
    return false
  }
}

async function fetchWithRefresh<T>(url: string, options: RequestInit = {}): Promise<T> {
  const baseOptions: RequestInit = { credentials: 'include', ...options }
  let res = await fetch(url, baseOptions)
  
  if (res.status === 401) {
    const refreshed = await refreshToken()
    if (refreshed) {
      // Retry with new cookies
      res = await fetch(url, baseOptions)
    } else {
      // Refresh failed, redirect
      if (typeof window !== 'undefined') window.location.href = '/'
      throw new Error('Session expired')
    }
  }
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    const detail = (errorData as any).detail
    throw new Error(detail || `API error: ${res.status}`)
  }
  return res.json()
}

export const api = {
  async get<T>(endpoint: string): Promise<T> {
    return fetchWithRefresh<T>(`${API_URL}${endpoint}`)
  },

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    const isFormData = typeof FormData !== 'undefined' && data instanceof FormData
    return fetchWithRefresh<T>(`${API_URL}${endpoint}`, {
      method: 'POST',
      headers: isFormData ? undefined : { 'Content-Type': 'application/json' },
      body: data ? (isFormData ? (data as BodyInit) : JSON.stringify(data)) : undefined
    })
  },

  async put<T>(endpoint: string, data: unknown): Promise<T> {
    return fetchWithRefresh<T>(`${API_URL}${endpoint}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  },

  async delete<T>(endpoint: string): Promise<T> {
    return fetchWithRefresh<T>(`${API_URL}${endpoint}`, {
      method: 'DELETE'
    })
  },

  getStreamUrl(endpoint: string): string {
    return `${API_URL}${endpoint}`
  },

  getAuthHeaders(): HeadersInit {
    return {}
  }
}
