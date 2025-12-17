export const API_URL = process.env.NEXT_PUBLIC_API_URL || ''

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

type FetchJsonConfig = {
  refreshOn401?: boolean
}

async function fetchWithSession(url: string, options: RequestInit = {}, config: FetchJsonConfig = {}): Promise<Response> {
  const baseOptions: RequestInit = { credentials: 'include', ...options }
  let res = await fetch(url, baseOptions)

  const refreshOn401 = config.refreshOn401 !== false
  if (refreshOn401 && res.status === 401) {
    const refreshed = await refreshToken()
    if (refreshed) {
      res = await fetch(url, baseOptions)
    } else {
      throw new Error('Session expired')
    }
  }

  return res
}

async function parseErrorPayload(res: Response): Promise<{ message: string; requestId?: string }> {
  const contentType = res.headers.get('content-type') || ''
  let data: any = null
  let text: string | null = null

  if (contentType.includes('application/json')) {
    data = await res.json().catch(() => null)
  } else {
    text = await res.text().catch(() => null)
    try {
      data = text ? JSON.parse(text) : null
    } catch {
      // ignore
    }
  }

  const detail = data?.detail ?? data?.error?.message ?? data?.message
  const requestId = data?.request_id ?? data?.error?.request_id
  const message = detail || text || `API error: ${res.status}`
  return { message, requestId }
}

async function fetchJson<T>(url: string, options: RequestInit = {}, config: FetchJsonConfig = {}): Promise<T> {
  const res = await fetchWithSession(url, options, config)
  
  if (!res.ok) {
    const { message, requestId } = await parseErrorPayload(res)
    throw new Error(requestId ? `${message} (request_id: ${requestId})` : message)
  }

  if (res.status === 204) return undefined as T
  return res.json()
}

async function fetchRaw(url: string, options: RequestInit = {}, config: FetchJsonConfig = {}): Promise<Response> {
  const res = await fetchWithSession(url, options, config)
  if (!res.ok) {
    const { message, requestId } = await parseErrorPayload(res)
    throw new Error(requestId ? `${message} (request_id: ${requestId})` : message)
  }
  return res
}

export const api = {
  async get<T>(endpoint: string): Promise<T> {
    return fetchJson<T>(`${API_URL}${endpoint}`)
  },

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    const isFormData = typeof FormData !== 'undefined' && data instanceof FormData
    return fetchJson<T>(`${API_URL}${endpoint}`, {
      method: 'POST',
      headers: isFormData ? undefined : { 'Content-Type': 'application/json' },
      body: data ? (isFormData ? (data as BodyInit) : JSON.stringify(data)) : undefined
    })
  },

  async put<T>(endpoint: string, data: unknown): Promise<T> {
    return fetchJson<T>(`${API_URL}${endpoint}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  },

  async delete<T>(endpoint: string): Promise<T> {
    return fetchJson<T>(`${API_URL}${endpoint}`, {
      method: 'DELETE'
    })
  },

  async request(endpoint: string, options: RequestInit = {}): Promise<Response> {
    return fetchRaw(`${API_URL}${endpoint}`, options)
  },

  getStreamUrl(endpoint: string): string {
    return `${API_URL}${endpoint}`
  },

  getAuthHeaders(): HeadersInit {
    return {}
  }
}

export const authApi = {
  async login(email: string, password: string) {
    return fetchJson<{ access_token: string; refresh_token: string; token_type: string }>(
      `${API_URL}/api/auth/login`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      },
      { refreshOn401: false }
    )
  },

  async register(email: string, username: string, password: string) {
    return fetchJson<{ access_token: string; refresh_token: string; token_type: string }>(
      `${API_URL}/api/auth/register`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, username, password })
      },
      { refreshOn401: false }
    )
  },

  async me() {
    return api.get<{ id: number; username: string; email: string; global_role?: string; email_notifications_enabled?: boolean }>(
      '/api/auth/me'
    )
  },

  async logout() {
    return fetchJson<{ success: boolean }>(
      `${API_URL}/api/auth/logout`,
      { method: 'POST' },
      { refreshOn401: false }
    )
  }
}
