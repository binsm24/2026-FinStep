import { useState } from 'react'
import {
  ArrowRight,
  BadgeAlert,
  Building2,
  ChevronLeft,
  CircleDollarSign,
  ShieldCheck,
  Siren,
  Sparkles,
  WalletCards,
} from 'lucide-react'
import './App.css'

type Scenario = {
  id: string
  title: string
  subtitle: string
  description: string
  icon: typeof Building2
  color: string
  background: string
  warningSignals: string[]
  placeholder: string
  recommendedActions: string[]
}

type AnalysisResult = {
  scenario_id: string
  scenario_title: string
  score: number
  risk_level: 'low' | 'medium' | 'high'
  risk_label: string
  detected_actions: string[]
  feedback: string
  recommended_actions: string[]
}

const scenarios: Scenario[] = [
  {
    id: 'jeonse-fraud',
    title: '전세사기',
    subtitle: '계약 전 위험 신호를 확인해보세요.',
    description:
      '시세보다 저렴한 매물과 계약을 서두르는 상황에서 어떻게 대응할지 판단해봅니다.',
    icon: Building2,
    color: '#4263eb',
    background: '#edf2ff',
    warningSignals: [
      '시세보다 지나치게 저렴한 가격',
      '오늘 안에 계약하라는 압박',
      '등기부등본 확인을 나중으로 미룸',
    ],
    placeholder:
      '예: 등기부등본과 집주인 정보를 확인하고 주변 시세를 조사한 뒤 계약 여부를 결정한다.',
    recommendedActions: [
      '계약 전 등기부등본 확인하기',
      '임대인이 실제 소유자인지 확인하기',
      '주변 전세 시세 확인하기',
      '확인이 끝날 때까지 계약과 송금을 보류하기',
    ],
  },
  {
    id: 'voice-phishing',
    title: '보이스피싱',
    subtitle: '수사기관을 사칭한 전화에 대응해보세요.',
    description:
      '검찰청을 사칭해 송금을 요구하는 상황에서 올바른 대응을 선택해봅니다.',
    icon: Siren,
    color: '#e03131',
    background: '#fff0f0',
    warningSignals: [
      '수사기관 사칭',
      '안전계좌로 송금 요구',
      '주변에 알리지 말라는 요구',
      '시간 제한을 이용한 압박',
    ],
    placeholder:
      '예: 전화를 끊고 가족에게 알린 뒤 공식 기관 대표번호로 직접 확인한다.',
    recommendedActions: [
      '상대방의 전화를 즉시 끊기',
      '공식 대표번호로 직접 확인하기',
      '송금하거나 인증번호를 알려주지 않기',
      '가족이나 지인에게 상황 알리기',
    ],
  },
  {
    id: 'investment-fraud',
    title: '투자사기',
    subtitle: '고수익 보장 제안을 판단해보세요.',
    description:
      '원금 보장과 높은 수익률을 내세운 투자 제안의 위험성을 확인해봅니다.',
    icon: CircleDollarSign,
    color: '#0ca678',
    background: '#e6fcf5',
    warningSignals: [
      '한 달 안에 20% 수익 보장',
      '원금 보장',
      '오늘만 가능한 기회라는 주장',
      '즉시 입금을 유도하는 압박',
    ],
    placeholder:
      '예: 수익률이 지나치게 높으므로 금융회사 등록 여부를 확인하고 투자를 보류한다.',
    recommendedActions: [
      '원금 보장과 고수익 약속을 의심하기',
      '금융회사와 상품의 공식 등록 여부 확인하기',
      '확인되지 않은 계좌로 송금하지 않기',
      '충분히 확인할 때까지 투자 보류하기',
    ],
  },
]

function App() {
  const [page, setPage] = useState<
    'home' | 'simulator' | 'scenario' | 'result'
  >('home')

  const [selectedScenario, setSelectedScenario] =
    useState<Scenario | null>(null)

  const [analysisResult, setAnalysisResult] =
    useState<AnalysisResult | null>(null)

  const handleScenarioSelect = (scenario: Scenario) => {
    setSelectedScenario(scenario)
    setPage('scenario')
  }

  const handleAnalysisComplete = (result: AnalysisResult) => {
    setAnalysisResult(result)
    setPage('result')
  }

  if (page === 'result' && analysisResult && selectedScenario) {
    return (
      <ResultPage
        scenario={selectedScenario}
        result={analysisResult}
        onBack={() => setPage('scenario')}
        onHome={() => {
          setSelectedScenario(null)
          setAnalysisResult(null)
          setPage('home')
        }}
      />
    )
  }

  if (page === 'scenario' && selectedScenario) {
    return (
      <ScenarioPage
        scenario={selectedScenario}
        onBack={() => setPage('simulator')}
        onAnalysisComplete={handleAnalysisComplete}
      />
    )
  }

  if (page === 'simulator') {
    return (
      <SimulatorPage
        onBack={() => setPage('home')}
        onSelectScenario={handleScenarioSelect}
      />
    )
  }

  return <HomePage onStart={() => setPage('simulator')} />
}

function Header({ onLogoClick }: { onLogoClick: () => void }) {
  return (
    <header className="header">
      <button className="logo-button" onClick={onLogoClick}>
        <span className="logo-mark">
          <Sparkles size={17} strokeWidth={2.5} />
        </span>
        <span className="logo-text">FinStep</span>
      </button>

      <div className="header-caption">금융을 이해하는 첫걸음</div>
    </header>
  )
}

function HomePage({ onStart }: { onStart: () => void }) {
  return (
    <div className="app-shell">
      <Header onLogoClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} />

      <main>
        <section className="hero-section">
          <div className="hero-copy">
            <div className="eyebrow">
              <ShieldCheck size={16} />
              대학생 금융 리터러시 플랫폼
            </div>

            <h1>
              금융 위험 상황,
              <br />
              <span>직접 판단해보세요.</span>
            </h1>

            <p className="hero-description">
              FinStep는 대학생과 사회초년생이 금융 사기 상황을
              직접 체험하고, 더 안전한 선택을 연습할 수 있도록 돕습니다.
            </p>

            <button className="primary-button" onClick={onStart}>
              금융 위험 시뮬레이터 시작
              <ArrowRight size={19} />
            </button>

            <div className="hero-note">
              <BadgeAlert size={16} />
              실제 생활에서 마주할 수 있는 상황을 바탕으로 구성했어요.
            </div>
          </div>

          <div className="hero-visual">
            <div className="visual-glow" />
            <div className="phone-card">
              <div className="phone-top">
                <span className="phone-dot" />
                <span>FinStep Simulator</span>
              </div>

              <div className="phone-question">
                <span className="question-label">TODAY'S SCENARIO</span>
                <h3>검찰청입니다.</h3>
                <p>계좌가 범죄에 이용되었습니다.</p>
              </div>

              <div className="phone-choice danger-choice">
                <span>?</span>
                바로 송금한다
              </div>

              <div className="phone-choice safe-choice">
                <span>✓</span>
                공식 기관에 확인한다
              </div>

              <div className="phone-bottom">
                <span>나의 판단을 분석해보세요</span>
                <ArrowRight size={16} />
              </div>
            </div>

            <div className="floating-card floating-card-top">
              <ShieldCheck size={18} />
              <div>
                <strong>안전한 선택</strong>
                <span>공식 경로로 확인하기</span>
              </div>
            </div>

            <div className="floating-card floating-card-bottom">
              <WalletCards size={18} />
              <div>
                <strong>3가지 시나리오</strong>
                <span>전세사기 · 보이스피싱 · 투자사기</span>
              </div>
            </div>
          </div>
        </section>

        <section className="feature-section">
          <div className="section-heading">
            <div>
              <span className="section-label">WHY FINSTEP</span>
              <h2>알고, 판단하고, 대비하는 금융 습관</h2>
            </div>
            <p>
              어려운 금융 지식을 외우는 대신,
              실제 상황 속에서 올바른 대응을 연습해보세요.
            </p>
          </div>

          <div className="feature-grid">
            <FeatureCard
              icon={<Siren size={23} />}
              number="01"
              title="상황을 직접 체험해요"
              description="실제 생활에서 일어날 수 있는 금융 위험 상황을 시뮬레이션합니다."
            />
            <FeatureCard
              icon={<BadgeAlert size={23} />}
              number="02"
              title="나의 대응을 확인해요"
              description="서술형 답변을 바탕으로 위험 행동과 예방 행동을 분석합니다."
            />
            <FeatureCard
              icon={<ShieldCheck size={23} />}
              number="03"
              title="더 나은 선택을 배워요"
              description="상황별 판단 근거와 안전한 대응 방법을 쉽게 확인합니다."
            />
          </div>
        </section>

        <section className="cta-section">
          <div>
            <span className="section-label light-label">START YOUR FINANCIAL STEP</span>
            <h2>첫 번째 금융 위험 상황을<br />확인해볼까요?</h2>
          </div>
          <button className="light-button" onClick={onStart}>
            시뮬레이터 시작하기
            <ArrowRight size={18} />
          </button>
        </section>
      </main>

      <footer className="footer">
        <span className="footer-logo">FinStep</span>
        <span>금융을 이해하는 첫걸음</span>
      </footer>
    </div>
  )
}

function FeatureCard({
  icon,
  number,
  title,
  description,
}: {
  icon: React.ReactNode
  number: string
  title: string
  description: string
}) {
  return (
    <article className="feature-card">
      <div className="feature-card-top">
        <div className="feature-icon">{icon}</div>
        <span>{number}</span>
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
    </article>
  )
}

function SimulatorPage({
  onBack,
  onSelectScenario,
}: {
  onBack: () => void
  onSelectScenario: (scenario: Scenario) => void
}) {
  return (
    <div className="app-shell">
      <Header onLogoClick={onBack} />

      <main className="simulator-main">
        <button className="back-button" onClick={onBack}>
          <ChevronLeft size={18} />
          홈으로 돌아가기
        </button>

        <section className="simulator-heading">
          <span className="section-label">FINANCIAL RISK SIMULATOR</span>
          <h1>어떤 상황을<br /><span>체험해볼까요?</span></h1>
          <p>
            상황을 읽고 내가 어떻게 대응할지 작성해보세요.
            <br />
            답변을 분석해 금융 위험 대응 수준을 알려드릴게요.
          </p>
        </section>

        <section className="scenario-grid">
          {scenarios.map((scenario) => {
            const Icon = scenario.icon

            return (
              <button
                className="scenario-card"
                key={scenario.id}
                onClick={() => onSelectScenario(scenario)}
              >
                <div
                  className="scenario-icon"
                  style={{
                    color: scenario.color,
                    backgroundColor: scenario.background,
                  }}
                >
                  <Icon size={28} />
                </div>

                <div className="scenario-card-content">
                  <span className="scenario-category">SCENARIO</span>
                  <h2>{scenario.title}</h2>
                  <h3>{scenario.subtitle}</h3>
                  <p>{scenario.description}</p>
                </div>

                <div className="scenario-arrow">
                  <ArrowRight size={19} />
                </div>
              </button>
            )
          })}
        </section>

        <div className="simulator-tip">
          <ShieldCheck size={19} />
          <p>
            이 시뮬레이터는 금융 교육을 위한 콘텐츠입니다.
            실제 금융 거래 전에는 반드시 공식 기관과 전문가에게 확인하세요.
          </p>
        </div>
      </main>
    </div>
  )
}

function ScenarioPage({
  scenario,
  onBack,
  onAnalysisComplete,
}: {
  scenario: Scenario
  onBack: () => void
  onAnalysisComplete: (result: AnalysisResult) => void
}) {
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  const [answer, setAnswer] = useState('')

  const Icon = scenario.icon

  const handleSubmit = async () => {
  if (!answer.trim()) {
    setErrorMessage('대응 방법을 작성해주세요.')
    return
  }

  setIsLoading(true)
  setErrorMessage('')

  try {
    const response = await fetch(
      'http://localhost:8000/api/simulators/analyze',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          scenario_id: scenario.id,
          answer: answer.trim(),
        }),
      },
    )

    if (!response.ok) {
      throw new Error('분석 요청에 실패했습니다.')
    }

    const result: AnalysisResult = await response.json()
    onAnalysisComplete(result)
  } catch (error) {
    console.error(error)
    setErrorMessage(
      '서버와 연결할 수 없습니다. 백엔드 서버가 실행 중인지 확인해주세요.',
    )
  } finally {
    setIsLoading(false)
  }
}
  return (
    <div className="app-shell">
      <Header onLogoClick={onBack} />

      <main className="scenario-main">
        <button className="back-button" onClick={onBack}>
          <ChevronLeft size={18} />
          시나리오 선택으로 돌아가기
        </button>

        <div
          className="scenario-detail-icon"
          style={{
            color: scenario.color,
            backgroundColor: scenario.background,
          }}
        >
          <Icon size={31} />
        </div>

        <section className="scenario-detail-heading">
          <span className="section-label">SCENARIO 01</span>
          <h1>{scenario.title}</h1>
          <p>{scenario.subtitle}</p>
        </section>

        <section className="scenario-detail-layout">
          <article className="situation-card">
            <div className="situation-card-header">
              <div>
                <span className="card-label">SITUATION</span>
                <h2>이런 상황이라면?</h2>
              </div>
              <BadgeAlert size={22} />
            </div>

            <div className="situation-description">
              {scenario.description.split('\n\n').map((paragraph, index) => (
                <p key={index}>{paragraph}</p>
              ))}
            </div>

            <div className="warning-signal-box">
              <div className="warning-title">
                <BadgeAlert size={17} />
                상황 속 위험 신호
              </div>

              <ul>
                {scenario.warningSignals.map((signal) => (
                  <li key={signal}>{signal}</li>
                ))}
              </ul>
            </div>
          </article>

          <article className="answer-card">
            <div className="answer-card-header">
              <span className="card-label">YOUR RESPONSE</span>
              <h2>어떻게 대응하시겠습니까?</h2>
              <p>
                정답을 찾기보다, 현재 상황에서 본인이 할 행동을
                자유롭게 작성해주세요.
              </p>
            </div>

            <textarea
              value={answer}
              onChange={(event) => setAnswer(event.target.value)}
              placeholder={scenario.placeholder}
              maxLength={500}
            />

            <div className="answer-footer">
              {errorMessage && (
                <p className="form-error">
                  {errorMessage}
                </p>
              )}
              <span>{answer.length}/500</span>
              <button
                className="primary-button"
                onClick={handleSubmit}
                disabled={isLoading}
              >
                {isLoading ? '분석 중...' : '답변 분석하기'}
                {!isLoading && <ArrowRight size={18} />}
              </button>
            </div>
          </article>
        </section>

        <div className="simulator-tip">
          <ShieldCheck size={19} />
          <p>
            답변은 금융 교육을 위한 분석에만 사용됩니다.
            실제 금융 거래 전에는 공식 기관에 반드시 확인하세요.
          </p>
        </div>
      </main>
    </div>
  )
}

function ResultPage({
  scenario,
  result,
  onBack,
  onHome,
}: {
  scenario: Scenario
  result: AnalysisResult
  onBack: () => void
  onHome: () => void
}) {
  const Icon = scenario.icon

  const resultClass =
    result.risk_level === 'low'
      ? 'result-low'
      : result.risk_level === 'medium'
        ? 'result-medium'
        : 'result-high'

  const resultIcon =
    result.risk_level === 'low'
      ? '✓'
      : result.risk_level === 'medium'
        ? '!'
        : '×'

  return (
    <div className="app-shell">
      <Header onLogoClick={onHome} />

      <main className="result-main">
        <button className="back-button" onClick={onBack}>
          <ChevronLeft size={18} />
          답변 화면으로 돌아가기
        </button>

        <section className="result-heading">
          <div
            className="result-scenario-icon"
            style={{
              color: scenario.color,
              backgroundColor: scenario.background,
            }}
          >
            <Icon size={26} />
          </div>

          <span className="section-label">ANALYSIS RESULT</span>
          <h1>
            {scenario.title} 상황에 대한
            <br />
            <span>나의 대응 결과</span>
          </h1>
        </section>

        <section className={`result-summary ${resultClass}`}>
          <div className="result-symbol">{resultIcon}</div>

          <div className="result-summary-content">
            <span>금융 위험 대응 수준</span>
            <h2>{result.risk_label}</h2>
            <p>
              현재 답변을 바탕으로 분석한 결과입니다.
              실제 상황에서는 반드시 공식 기관에 확인하세요.
            </p>
          </div>

          <div className="result-score">
            <span>SCORE</span>
            <strong>
              {result.score > 0 ? '+' : ''}
              {result.score}
            </strong>
          </div>
        </section>

        <section className="result-grid">
          <article className="result-card">
            <div className="result-card-title">
              <h2>발견된 행동</h2>
              <span>{result.detected_actions.length}</span>
            </div>

            {result.detected_actions.length > 0 ? (
              <ul className="action-list">
                {result.detected_actions.map((action) => (
                  <li key={action}>
                    <span>✓</span>
                    {action}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="empty-message">
                명확한 행동이 충분히 확인되지 않았습니다.
              </p>
            )}
          </article>

          <article className="result-card">
            <div className="result-card-title">
              <h2>분석 피드백</h2>
            </div>

            <p className="feedback-text">{result.feedback}</p>
          </article>
        </section>

        <section className="recommendation-card">
          <div className="recommendation-heading">
            <ShieldCheck size={22} />
            <div>
              <span className="section-label">SAFER RESPONSE</span>
              <h2>이렇게 대응해보세요</h2>
            </div>
          </div>

          <ul>
            {result.recommended_actions.map((action, index) => (
              <li key={action}>
                <span>{index + 1}</span>
                {action}
              </li>
            ))}
          </ul>
        </section>

        <div className="result-actions">
          <button className="secondary-button" onClick={onBack}>
            다시 답변하기
          </button>
          <button className="primary-button" onClick={onHome}>
            처음으로 돌아가기
            <ArrowRight size={18} />
          </button>
        </div>

        <div className="simulator-tip">
          <ShieldCheck size={19} />
          <p>
            FinStep의 분석 결과는 금융 교육을 위한 참고 자료입니다.
            실제 금융 문제는 경찰청, 금융감독원 등 공식 기관에 문의하세요.
          </p>
        </div>
      </main>
    </div>
  )
}

export default App
