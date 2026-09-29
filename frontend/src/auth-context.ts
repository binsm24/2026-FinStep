import { createContext, useContext } from 'react'

export type User = { id: string; name: string; email: string }
export type AuthState = {
  user: User | null
  loading: boolean
  configured: boolean
  error: string
  openLogin: () => void
  logout: () => Promise<void>
  refresh: () => Promise<void>
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('AuthProvider is required')
  return value
}
