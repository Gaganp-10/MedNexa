import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import {
  apiFetch,
  setAccessToken,
  setRefreshToken,
  getRefreshToken,
  clearAuth,
  refreshAccessToken,
  onAuthStateChange,
} from '@/api/client'
import type { AuthMeResponse, TokenResponse } from '@/types/api'

interface AuthContextType {
  user: AuthMeResponse | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (username: string, password: string) => Promise<AuthMeResponse>
  logout: () => void
  reloadUser: () => Promise<AuthMeResponse | null>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthMeResponse | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)

  const reloadUser = useCallback(async (): Promise<AuthMeResponse | null> => {
    try {
      const me = await apiFetch<AuthMeResponse>('/auth/me/')
      setUser(me)
      return me
    } catch {
      setUser(null)
      return null
    }
  }, [])

  // Check initial authentication on app mount via silent refresh
  useEffect(() => {
    let isMounted = true
    const initAuth = async () => {
      const refresh = getRefreshToken()
      if (refresh) {
        const token = await refreshAccessToken()
        if (token && isMounted) {
          await reloadUser()
        }
      }
      if (isMounted) {
        setIsLoading(false)
      }
    }

    initAuth()

    const unsubscribe = onAuthStateChange((authed) => {
      if (!authed) {
        setUser(null)
      }
    })

    return () => {
      isMounted = false
      unsubscribe()
    }
  }, [reloadUser])

  const login = async (username: string, password: string): Promise<AuthMeResponse> => {
    setIsLoading(true)
    try {
      // POST /api/token/
      const tokenData = await apiFetch<TokenResponse>('/token/', {
        method: 'POST',
        skipAuth: true,
        body: JSON.stringify({ username, password }),
      })

      // Store access in memory, refresh in localStorage
      setAccessToken(tokenData.access)
      setRefreshToken(tokenData.refresh)

      // Role-based routing info: GET /api/auth/me/
      const me = await apiFetch<AuthMeResponse>('/auth/me/')
      setUser(me)
      return me
    } finally {
      setIsLoading(false)
    }
  }

  const logout = () => {
    clearAuth()
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        reloadUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
