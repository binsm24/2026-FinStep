import { Check, CircleAlert, History, ShieldCheck } from 'lucide-react'
import ConversationHistory from './ConversationHistory'
import type { DiagnosisReport as Report, ScoredCategory } from './diagnosis'
import './Report.css'

const categoryLabels: Record<string, string> = {
  protection: '요구 거절·접촉 중단', verification: '독립적인 확인', support: '주변에 도움 요청',
  money: '검증 전 송금·투자', personal_info: '민감정보 제공', contract: '검증 전 계약',
  unverified_compliance: '확인 없이 지시 수용',
}
const adjustmentLabels: Record<string, string> = {
  maximum_base: '안전 행동 기준점은 최대 100점으로 반영했어요.',
  no_official_verification: '독립적인 공식 확인이 없어 안전 행동 기준점을 95점으로 제한했어요.',
  score_bounds: '최종 점수가 0~100점 범위를 벗어나지 않도록 조정했어요.',
  risk_continues_cap: '마지막까지 위험 행동이 이어져 최종 점수를 최대 39점으로 제한했어요.',
}

export function ScoreValue({ report }: { report: Pick<Report, 'score' | 'scoring_version'> }) {
  if (report.scoring_version !== 'behavior-v1') return <span className="score-unavailable">이전 기준</span>
  if (report.score == null) return <span className="score-unavailable">미산정</span>
  return <><strong>{report.score}</strong><span className="score-denominator"> / 100점</span></>
}

function CategoryRow({ item, risk = false }: { item: ScoredCategory; risk?: boolean }) {
  return <li className="score-evidence-row">
    <div><span className="score-category-name">{categoryLabels[item.category] ?? '확인된 대응 행동'}</span>
      <blockquote>“{item.action.evidence}”</blockquote>
    </div>
    <strong className={risk ? 'points-negative' : 'points-positive'}>{risk ? '−' : '+'}{item.points}</strong>
  </li>
}

export default function DiagnosisReport({ report, showConversation = false }: { report: Report; showConversation?: boolean }) {
  const current = report.scoring_version === 'behavior-v1'
  const scored = current && report.score != null
  const breakdown = current ? report.score_breakdown : null
  return <div className="diagnosis-report">
    <section className={`diagnosis-overview tone-${report.risk_level}`} aria-label="진단 요약">
      <div className="diagnosis-outcome">
        <span className="report-eyebrow">이번 상황에서의 대응</span>
        <h2><span className="outcome-icon" aria-hidden="true">{report.risk_level === 'low' ? <ShieldCheck size={24} /> : <CircleAlert size={24} />}</span>{report.risk_label}</h2>
        {!['위험 행동 지속', '확인 전 보류'].includes(report.risk_label) && <p>{report.summary}</p>}
      </div>
      <div className="diagnosis-score">
        <span>이번 시뮬레이션 대응 점수</span>
        <div className="score-value"><ScoreValue report={report} /></div>
        {scored && <meter min={0} max={100} value={report.score!} aria-label="이번 시뮬레이션 대응 점수" />}
        <p>{!current ? '저장 당시의 이전 채점 기준으로 평가한 결과예요. 현재 점수와 직접 비교하지 마세요.' : report.score == null ? '행동을 충분히 판단하기 어려워 점수를 확정하지 않았어요.' : '이번에 확인된 행동을 평가한 점수예요.'}</p>
      </div>
    </section>

    {breakdown && <section className="report-panel score-breakdown" aria-labelledby="score-breakdown-title">
      <div className="report-panel-heading"><div><span className="report-eyebrow">점수의 이유</span><h2 id="score-breakdown-title">내 대응이 어떻게 반영됐나요?</h2></div><span className="report-tag">행동별 채점</span></div>
      {report.score == null && <p className="report-notice">아래는 확인된 행동의 내역이에요. 자료가 부족해 최종 점수는 미산정으로 남겨두었어요.</p>}
      <div className="score-ledger">
        <div className="score-base"><span>기본점</span><strong>{breakdown.base_score == null ? '미적용' : `${breakdown.base_score}점`}</strong></div>
        <div className="score-columns">
          <section><h3><Check size={17} /> 보호에 도움이 된 대응 <span>+{breakdown.safe_points}</span></h3>
            {breakdown.safe_categories.length ? <ul>{breakdown.safe_categories.map(item => <CategoryRow key={item.category} item={item} />)}</ul> : <p className="report-muted">가점으로 반영할 대응이 확인되지 않았어요.</p>}
          </section>
          <section><h3><CircleAlert size={17} /> 보완이 필요한 대응 <span>−{breakdown.risk_penalty}</span></h3>
            {breakdown.risk_categories.length ? <ul>{breakdown.risk_categories.map(item => <CategoryRow key={item.category} item={item} risk />)}</ul> : <p className="report-muted">감점으로 반영된 위험 행동이 없어요.</p>}
          </section>
        </div>
        <div className="score-total"><span>최종 대응 점수</span><strong>{report.score == null ? '미산정' : `${report.score} / 100점`}</strong></div>
      </div>
      {breakdown.adjustments.length > 0 && <ul className="score-adjustments">{breakdown.adjustments.map((item, index) => <li key={`${item.reason}-${index}`}>{adjustmentLabels[item.reason] ?? '채점 기준에 따른 점수 제한을 적용했어요.'}</li>)}</ul>}
    </section>}

    <div className="report-behavior-grid">
      <section className="report-panel"><h2><ShieldCheck size={20} /> 확인된 안전 행동 <span className="report-count">{report.safe_actions.length}</span></h2>
        {report.safe_actions.length ? <ul className="report-action-list">{report.safe_actions.map((a, i) => <li key={i}>{a}</li>)}</ul> : <p className="report-muted">명확하게 확인된 안전 행동이 없어요.</p>}
      </section>
      <section className="report-panel"><h2><CircleAlert size={20} /> 확인된 위험 행동 <span className="report-count">{report.risky_actions.length}</span></h2>
        {report.risky_actions.length ? <ul className="report-action-list risk-action-list">{report.risky_actions.map((a, i) => <li key={i}>{a}</li>)}</ul> : <p className="report-muted">명확하게 확인된 위험 행동이 없어요.</p>}
      </section>
    </div>
    <section className="report-panel report-recommendations"><h2><ShieldCheck size={21} /> 다음에는 이렇게 대응해 보세요</h2><ol>{report.recommended_actions.map((a, i) => <li key={i}><span>{i + 1}</span>{a}</li>)}</ol></section>
    {showConversation && <details className="report-panel report-conversation"><summary><History size={20} /><span>당시 대화와 내 답변 다시 보기</span><span className="conversation-expand">펼치기</span></summary>
      {(report.conversation_history?.length ?? 0) > 0 ? <ConversationHistory entries={report.conversation_history!.map(e => ({ ...e, isUser: e.speaker === '나' }))} /> : <p className="report-muted">이 결과에는 저장된 대화 기록이 없어요.</p>}
    </details>}
  </div>
}
