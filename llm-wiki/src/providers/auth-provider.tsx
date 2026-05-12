'use client'

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { AuthUser } from '@/lib/types'
import { authService } from '@/services/auth'

type AuthContextValue = {
  user: AuthUser | null
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  hasRole: (...roles: string[]) => boolean
  hasPermission: (...permissions: string[]) => boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)
const ROLE_ORDER: Record<string, number> = { reader: 0, editor: 1, reviewer: 2, admin: 3 }

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const storedToken = window.localStorage.getItem('llm-wiki-auth-token')
    const storedUser = window.localStorage.getItem('llm-wiki-auth-user')
    if (storedToken) setToken(storedToken)
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser) as AuthUser)
      } catch {
        window.localStorage.removeItem('llm-wiki-auth-user')
      }
    }
    if (!storedToken) {
      setIsLoading(false)
      return
    }
    authService.me()
      .then(nextUser => {
        setUser(nextUser)
        window.localStorage.setItem('llm-wiki-auth-user', JSON.stringify(nextUser))
      })
      .catch(() => {
        window.localStorage.removeItem('llm-wiki-auth-token')
        window.localStorage.removeItem('llm-wiki-auth-user')
        setToken(null)
        setUser(null)
      })
      .finally(() => setIsLoading(false))
  }, [])

  const value = useMemo<AuthContextValue>(() => ({
    user,
    token,
    isLoading,
    login: async (email: string, password: string) => {
      const response = await authService.login(email, password)
      window.localStorage.setItem('llm-wiki-auth-token', response.token)
      window.localStorage.setItem('llm-wiki-auth-user', JSON.stringify(response.user))
      window.localStorage.setItem('llm-wiki-user', response.user.name)
      setToken(response.token)
      setUser(response.user)
    },
    logout: async () => {
      try {
        await authService.logout()
      } finally {
        window.localStorage.removeItem('llm-wiki-auth-token')
        window.localStorage.removeItem('llm-wiki-auth-user')
        setToken(null)
        setUser(null)
      }
    },
    hasRole: (...roles: string[]) => {
      if (!user) return false
      if (roles.includes(user.role)) return true
      const minimum = Math.min(...roles.map(role => ROLE_ORDER[role] ?? 99))
      return (ROLE_ORDER[user.role] ?? -1) >= minimum
    },
    hasPermission: (...permissions: string[]) => {
      if (!user) return false
      const userPermissions = new Set(user.permissions || [])
      return permissions.some(permission => userPermissions.has(permission) || userPermissions.has('*'))
    },
  }), [isLoading, token, user])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
