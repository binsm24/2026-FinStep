import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { apiJson } from './api'
import { AuthContext, type User } from './auth-context'
import GoogleSignIn from './GoogleSignIn'

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [configured, setConfigured] = useState(false)
  const [error, setError] = useState('')
  const [loginOpen, setLoginOpen] = useState(false)
  const generation = useRef(0)
  const channel = useRef<BroadcastChannel | null>(null)

  const refresh = useCallback(async () => {
    const current = ++generation.current
    try {
      const response = await apiJson<{ user: User | null; google_configured: boolean }>('/api/auth/me')
      if (current !== generation.current) return
      setUser(response.user); setConfigured(response.google_configured); setError('')
    } catch {
      if (current === generation.current) {
        setUser(null); setError('로그인 상태를 확인할 수 없습니다. 다시 확인해 주세요.')
      }
    } finally {
      if (current === generation.current) setLoading(false)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    const current = ++generation.current
    apiJson<{ user: User | null; google_configured: boolean }>('/api/auth/me', { signal: controller.signal })
      .then(response => {
        if (controller.signal.aborted || current !== generation.current) return
        setUser(response.user); setConfigured(response.google_configured); setError('')
      })
      .catch(() => {
        if (!controller.signal.aborted && current === generation.current) {
          setUser(null); setError('로그인 상태를 확인할 수 없습니다. 다시 확인해 주세요.')
        }
      })
      .finally(() => { if (!controller.signal.aborted && current === generation.current) setLoading(false) })
    const changed = () => { void refresh() }
    const expired = () => { ++generation.current; setUser(null); setLoading(false) }
    window.addEventListener('focus', changed)
    window.addEventListener('finstep-auth-expired', expired)
    if ('BroadcastChannel' in window) {
      channel.current = new BroadcastChannel('finstep-auth')
      channel.current.onmessage = changed
    }
    return () => {
      controller.abort()
      window.removeEventListener('focus', changed)
      window.removeEventListener('finstep-auth-expired', expired)
      channel.current?.close()
    }
  }, [refresh])

  const signedIn = useCallback((next: User) => {
    ++generation.current
    setUser(next); setLoading(false); setError(''); setLoginOpen(false)
    channel.current?.postMessage('changed')
  }, [])

  const logout = useCallback(async () => {
    await apiJson('/api/auth/logout', { method: 'POST' })
    ++generation.current
    window.google?.accounts.id.disableAutoSelect()
    setUser(null)
    channel.current?.postMessage('changed')
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, configured, error, refresh, logout, openLogin: () => setLoginOpen(true) }}>
      {children}
      {loginOpen && <GoogleSignIn configured={configured} onSuccess={signedIn} onClose={() => setLoginOpen(false)} />}
    </AuthContext.Provider>
  )
}
