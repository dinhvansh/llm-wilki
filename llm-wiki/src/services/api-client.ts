const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? '/backend-api'

function getActorHeader() {
  if (typeof window === 'undefined') return 'Current User'
  return window.localStorage.getItem('llm-wiki-user') || 'Current User'
}

function getAuthToken() {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem('llm-wiki-auth-token')
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      'X-User': getActorHeader(),
      ...(getAuthToken() ? { Authorization: `Bearer ${getAuthToken()}` } : {}),
      ...init?.headers,
    },
    cache: 'no-store',
  })

  if (response.status === 401 && typeof window !== 'undefined' && !path.startsWith('/auth/login')) {
    window.localStorage.removeItem('llm-wiki-auth-token')
    window.localStorage.removeItem('llm-wiki-auth-user')
    window.localStorage.removeItem('llm-wiki-user')
    window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`
    throw new Error('Authentication required')
  }

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Request failed with status ${response.status}`)
  }

  return response.json() as Promise<T>
}
