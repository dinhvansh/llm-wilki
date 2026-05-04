import type { AuthUser } from '@/lib/types'
import { apiRequest } from './api-client'

export interface AuthResponse {
  token: string
  user: AuthUser
}

export const authService = {
  login(email: string, password: string) {
    return apiRequest<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  },
  me() {
    return apiRequest<AuthUser>('/auth/me')
  },
  logout() {
    return apiRequest<{ success: boolean }>('/auth/logout', { method: 'POST' })
  },
}

