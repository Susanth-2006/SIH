import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { apiGet, apiPost, getToken, setToken } from '../services/api'

const AuthContext = createContext(null)

const USER_KEY = 'uip_auth_user'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY)) || null
    } catch {
      return null
    }
  })
  const [ready, setReady] = useState(false)

  const logout = useCallback(() => {
    setToken(null)
    localStorage.removeItem(USER_KEY)
    setUser(null)
  }, [])

  useEffect(() => {
    const validate = async () => {
      const token = getToken()
      if (!token) {
        setReady(true)
        return
      }
      try {
        const me = await apiGet('/api/auth/me')
        setUser(me)
        localStorage.setItem(USER_KEY, JSON.stringify(me))
      } catch {
        logout()
      } finally {
        setReady(true)
      }
    }
    validate()
  }, [logout])

  useEffect(() => {
    const onUnauthorized = () => logout()
    window.addEventListener('uip:unauthorized', onUnauthorized)
    return () => window.removeEventListener('uip:unauthorized', onUnauthorized)
  }, [logout])

  const login = async (username, password) => {
    const data = await apiPost('/api/auth/login', { username, password })
    setToken(data.access_token)
    const me = data.user
    setUser(me)
    localStorage.setItem(USER_KEY, JSON.stringify(me))
    return me
  }

  return <AuthContext.Provider value={{ user, ready, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}