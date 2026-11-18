import { useEffect, useRef, useState } from 'react'
import { apiJson } from './api'
import type { User } from './auth-context'

type GoogleIdentity = {
  initialize: (options: { client_id: string; nonce: string; ux_mode: 'popup'; auto_select: boolean; callback: (reply: { credential: string }) => void }) => void
  renderButton: (element: HTMLElement, options: { theme: string; size: string; text: string; locale: string }) => void
  disableAutoSelect: () => void
}

declare global {
  interface Window { google?: { accounts: { id: GoogleIdentity } } }
}

let scriptPromise: Promise<void> | undefined
function loadGoogle() {
  if (window.google?.accounts.id) return Promise.resolve()
  if (!scriptPromise) {
    scriptPromise = new Promise<void>((resolve, reject) => {
      const script = document.createElement('script')
      script.src = 'https://accounts.google.com/gsi/client'
      script.async = true
      script.onload = () => resolve()
      script.onerror = () => {
        script.remove()
        scriptPromise = undefined
        reject(new Error('구글 로그인 화면을 불러올 수 없습니다. 네트워크 상태를 확인해 주세요.'))
      }
      document.head.appendChild(script)
    })
  }
  return scriptPromise
}

export default function GoogleSignIn({ configured, onSuccess, onClose }: {
  configured: boolean; onSuccess: (user: User) => void; onClose: () => void
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const button = useRef<HTMLDivElement>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [ready, setReady] = useState(false)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const element = dialog.current
    element?.showModal()
    return () => element?.close()
  }, [])

  useEffect(() => {
    if (!configured) return
    let active = true
    let submitting = false
    const container = button.current
    async function prepare() {
      try {
        await loadGoogle()
        if (!active) return
        const challenge = await apiJson<{ client_id: string; nonce: string }>('/api/auth/challenge', { method: 'POST' })
        if (!active || !container || !window.google) return
        window.google.accounts.id.initialize({
          client_id: challenge.client_id, nonce: challenge.nonce, ux_mode: 'popup', auto_select: false,
          callback: async ({ credential }) => {
            if (!active || submitting) return
            submitting = true
            setBusy(true)
            setError('')
            try {
              const response = await apiJson<{ user: User }>('/api/auth/google', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ credential }),
              })
              if (active) onSuccess(response.user)
            } catch (e) {
              if (active) setError(e instanceof Error ? e.message : '로그인하지 못했습니다.')
            } finally {
              submitting = false
              if (active) setBusy(false)
            }
          },
        })
        window.google.accounts.id.renderButton(container, { theme: 'outline', size: 'large', text: 'signin_with', locale: 'ko' })
        setReady(true)
      } catch (e) {
        if (active) setError(e instanceof Error ? e.message : '로그인을 준비하지 못했습니다.')
      }
    }
    void prepare()
    return () => { active = false; container?.replaceChildren() }
  }, [configured, attempt, onSuccess])

  return (
    <dialog ref={dialog} className="auth-dialog" onCancel={onClose} aria-labelledby="login-title">
      <h2 id="login-title">구글 계정으로 로그인</h2>
      {!configured ? <p role="status">구글 로그인 기능을 준비 중입니다. 시뮬레이션과 학습은 로그인 없이 이용할 수 있어요.</p> : (
        <>
          {!ready && !error && <p role="status">로그인 버튼을 준비하고 있어요.</p>}
          <div className="google-signin-button" ref={button} hidden={busy} />
          {busy && <p role="status">계정을 확인하고 있어요.</p>}
          {error && <p role="alert" className="form-error">{error}</p>}
          {error && <button type="button" className="account-button" disabled={busy} onClick={() => {
            setError(''); setReady(false); setAttempt(attempt + 1)
          }}>로그인 다시 준비하기</button>}
        </>
      )}
      <button type="button" className="account-button" disabled={busy} onClick={onClose}>닫기</button>
    </dialog>
  )
}
