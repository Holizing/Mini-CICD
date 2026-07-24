import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { clearAuthToken, getAuthToken, setAuthToken } from '../authStorage'
import { authService } from '../services/authService'


const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const logout = useCallback(() => {
    clearAuthToken()
    setUser(null)
    setLoading(false)
  }, [])

  useEffect(() => {
    let active = true

    const restoreSession = async () => {
      if (!getAuthToken()) {
        if (active) {
          setLoading(false)
        }
        return
      }

      try {
        const currentAdmin = await authService.getCurrentAdmin()
        if (active) {
          setUser(currentAdmin)
        }
      } catch {
        clearAuthToken()
        if (active) {
          setUser(null)
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    restoreSession()
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    window.addEventListener('auth:unauthorized', logout)
    return () => window.removeEventListener('auth:unauthorized', logout)
  }, [logout])

  const login = useCallback(async (username, password) => {
    const result = await authService.login(username.trim(), password)
    setAuthToken(result.access_token)
    setUser(result.user)
    setLoading(false)
    return result.user
  }, [])

  const value = useMemo(
    () => ({
      user,
      loading,
      isAuthenticated: Boolean(user),
      login,
      logout,
    }),
    [loading, login, logout, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === null) {
    throw new Error('useAuth must be used inside AuthProvider')
  }
  return context
}
