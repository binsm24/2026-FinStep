import { useContext, useState } from 'react'
import { useAuth } from './auth-context'
import { ArchiveNavigation } from './navigation-context'

export default function AccountControls() {
  const auth = useAuth()
  const openArchive = useContext(ArchiveNavigation)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  return (
    <div className="account-controls">
      <button type="button" className="account-button" onClick={openArchive}>진단 결과 보관함</button>
      {auth.loading ? <span role="status">로그인 확인 중…</span> : auth.user ? (
        <>
          <span className="account-name" title={auth.user.email}>{auth.user.name} 님</span>
          <button type="button" className="account-button" disabled={busy} onClick={async () => {
            setBusy(true); setError('')
            try { await auth.logout() }
            catch (e) { setError(e instanceof Error ? e.message : '로그아웃하지 못했습니다.') }
            finally { setBusy(false) }
          }}>로그아웃</button>
        </>
      ) : <button type="button" className="account-button" onClick={auth.openLogin}>로그인</button>}
      {auth.error && <button type="button" className="account-button" onClick={() => { void auth.refresh() }}>로그인 상태 다시 확인</button>}
      {error && <span className="form-error" role="alert">{error}</span>}
    </div>
  )
}
