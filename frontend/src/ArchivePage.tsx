import { useEffect, useRef, useState } from 'react'
import { apiJson } from './api'
import ConversationHistory from './ConversationHistory'
import { useAuth } from './auth-context'

type SavedSummary = { id: string; scenario_title: string; risk_label: string; risk_level: 'low' | 'medium' | 'high' | 'unknown'; created_at: number }
type SavedDetail = SavedSummary & { result: {
  summary: string; completed_stage_count: number; total_stages: number
  safe_actions: string[]; risky_actions: string[]; recommended_actions: string[]
  conversation_history: { stage: number; speaker: string; message: string }[]
} }
const dateText = (stamp: number) => new Date(stamp * 1000).toLocaleString('ko-KR')

function UserArchive() {
  const [items, setItems] = useState<SavedSummary[]>([])
  const [offset, setOffset] = useState(0)
  const [retry, setRetry] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [detail, setDetail] = useState<SavedDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const detailRequest = useRef<AbortController | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    apiJson<{ items: SavedSummary[]; has_more: boolean }>(`/api/results?limit=20&offset=${offset}`, { signal: controller.signal })
      .then(data => {
        if (controller.signal.aborted) return
        setItems(data.items); setHasMore(data.has_more); setError('')
      })
      .catch(e => { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : '목록을 불러오지 못했습니다.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [offset, retry])

  useEffect(() => () => detailRequest.current?.abort(), [])

  const showDetail = async (id: string) => {
    detailRequest.current?.abort()
    const controller = new AbortController()
    detailRequest.current = controller
    setDetailLoading(true); setError('')
    try {
      const data = await apiJson<SavedDetail>(`/api/results/${encodeURIComponent(id)}`, { signal: controller.signal })
      if (!controller.signal.aborted) setDetail(data)
    } catch (e) {
      if (!controller.signal.aborted) setError(e instanceof Error ? e.message : '결과를 불러오지 못했습니다.')
    } finally { if (!controller.signal.aborted) setDetailLoading(false) }
  }

  if (detail) return (
    <section className={`saved-detail archive-risk-${detail.risk_level}`}>
      <button type="button" className="account-button" onClick={() => { setDetail(null); setError('') }}>보관함 목록으로</button>
      <h2>{detail.scenario_title} · {detail.risk_label}</h2>
      <p>저장 일시: {dateText(detail.created_at)}</p>
      <p>{detail.result.summary}</p>
      <p>응답 완료 단계: {detail.result.completed_stage_count} / {detail.result.total_stages}</p>
      <div className="archive-detail-grid">
        <section><h3>안전 행동</h3>{detail.result.safe_actions.length ? <ul>{detail.result.safe_actions.map((a, i) => <li key={i}>{a}</li>)}</ul> : <p>확인된 안전 행동이 없습니다.</p>}</section>
        <section><h3>위험 행동</h3>{detail.result.risky_actions.length ? <ul>{detail.result.risky_actions.map((a, i) => <li key={i}>{a}</li>)}</ul> : <p>확인된 위험 행동이 없습니다.</p>}</section>
      </div>
      <h3>안전한 대응 방법</h3>
      <ul>{detail.result.recommended_actions.map((a, i) => <li key={i}>{a}</li>)}</ul>
      <details>
        <summary>진단 당시 대화 기록 보기</summary>
        <section className="conversation-card archive-conversation-card">
          <ConversationHistory entries={detail.result.conversation_history.map(entry => ({ ...entry, isUser: entry.speaker === '나' }))} />
        </section>
      </details>
    </section>
  )

  return (
    <section aria-label="저장된 진단 목록">
      {(loading || detailLoading) && <p role="status">결과를 불러오는 중…</p>}
      {error && <div role="alert"><p className="form-error">{error}</p><button type="button" className="account-button" onClick={() => { setLoading(true); setRetry(retry + 1) }}>목록 다시 불러오기</button></div>}
      {!loading && !error && items.length === 0 && <div className="archive-empty">저장된 진단이 없습니다. 시뮬레이션을 마치고 ‘보관함에 저장’을 눌러보세요.</div>}
      {!loading && <div className="archive-list">{items.map(item => (
        <button type="button" className={`archive-item archive-risk-${item.risk_level}`} key={item.id} disabled={detailLoading} onClick={() => { void showDetail(item.id) }}>
          <strong>{item.scenario_title}</strong><span>{item.risk_label}</span><time dateTime={new Date(item.created_at * 1000).toISOString()}>{dateText(item.created_at)}</time><span>결과 보기 →</span>
        </button>
      ))}</div>}
      <div className="archive-pagination">
        <button type="button" className="account-button" disabled={offset === 0 || loading || detailLoading} onClick={() => { setLoading(true); setOffset(offset - 20) }}>이전</button>
        <span>{offset / 20 + 1}페이지</span>
        <button type="button" className="account-button" disabled={!hasMore || loading || detailLoading} onClick={() => { setLoading(true); setOffset(offset + 20) }}>다음</button>
      </div>
    </section>
  )
}

export default function ArchivePage() {
  const auth = useAuth()
  return (
    <main className="archive-main">
      <h1>진단 결과 보관함</h1>
      <p>내가 저장한 진단 결과를 다시 확인해 보세요.</p>
      {auth.loading ? <p role="status">로그인 상태를 확인하고 있어요.</p> : auth.user ? <UserArchive key={auth.user.id} /> : (
        <section className="archive-empty"><p>내 진단 결과를 보려면 로그인해 주세요.</p><button type="button" className="primary-button" onClick={auth.openLogin}>구글 로그인</button></section>
      )}
    </main>
  )
}
