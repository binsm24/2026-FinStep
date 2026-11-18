import { useEffect, useRef } from 'react'

export type ConversationEntry = {
  stage: number
  stageTitle?: string
  speaker: string
  message: string
  isUser?: boolean
  kind?: 'situation'
}

export default function ConversationHistory({ entries, followLatest = false }: {
  entries: ConversationEntry[]
  followLatest?: boolean
}) {
  const historyRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const history = historyRef.current
    if (followLatest && history) history.scrollTop = history.scrollHeight
  }, [entries, followLatest])
  useEffect(() => {
    const history = historyRef.current
    if (!followLatest || !history) return
    const observer = new ResizeObserver(() => { history.scrollTop = history.scrollHeight })
    observer.observe(history)
    return () => observer.disconnect()
  }, [followLatest])

  return (
    <div className="conversation-history" ref={historyRef} tabIndex={0} role="region" aria-label="시나리오 대화 기록">
      {entries.filter(entry => entry.kind !== 'situation').map((entry, index, visibleEntries) => (
        <div key={`${entry.stage}-${index}`}>
          {(index === 0 || visibleEntries[index - 1].stage !== entry.stage) && (
            <div className="conversation-stage-divider">
              <span>{entry.stage}단계{entry.stageTitle ? ` · ${entry.stageTitle}` : ''}</span>
            </div>
          )}
          {entry.kind === 'situation' ? <div className="scenario-context-message"><span>현재 상황</span><p>{entry.message}</p></div> : <div className={`message-row ${entry.isUser ? 'user-message-row' : ''}`}>
            <span className={`speaker-label ${entry.isUser ? 'user-speaker-label' : ''}`}>{entry.speaker}</span>
            <div className={`message-bubble ${entry.isUser ? 'user-message-bubble' : ''}`}>{entry.message}</div>
          </div>}
        </div>
      ))}
    </div>
  )
}
