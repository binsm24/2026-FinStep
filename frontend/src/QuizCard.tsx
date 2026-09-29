import { useRef, useState } from 'react'
import { ArrowRight } from 'lucide-react'
import { createQuizRound, type Quiz } from './quiz'

export default function QuizCard({ quizzes }: { quizzes: Quiz[] }) {
  const [round, setRound] = useState(() => createQuizRound(quizzes))
  const [position, setPosition] = useState(0)
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null)
  const [isSubmitted, setIsSubmitted] = useState(false)
  const heading = useRef<HTMLHeadingElement>(null)
  const quiz = round[position]

  if (!quiz) {
    return <article className="learning-quiz-card">준비된 퀴즈가 없습니다.</article>
  }

  const isCorrect = selectedAnswer === quiz.answer_index
  const isLast = position === round.length - 1

  const nextQuestion = () => {
    if (!isSubmitted) return
    if (isLast) {
      setRound(createQuizRound(quizzes, quiz.id))
      setPosition(0)
    } else {
      setPosition(position + 1)
    }
    setSelectedAnswer(null)
    setIsSubmitted(false)
    heading.current?.focus()
  }

  return (
    <article className="learning-quiz-card">
      <h2 ref={heading} tabIndex={-1}>확인 퀴즈</h2>
      <p className="quiz-question">{quiz.question}</p>

      <div className="quiz-options" role="group" aria-label="답 선택">
        {quiz.options.map((option, index) => (
          <button
            type="button"
            className={`quiz-option ${selectedAnswer === index ? 'quiz-option-selected' : ''} ${
              isSubmitted && index === quiz.answer_index ? 'quiz-option-correct' : ''
            } ${isSubmitted && selectedAnswer === index && !isCorrect ? 'quiz-option-wrong' : ''}`}
            key={`${quiz.id}-${index}`}
            aria-pressed={selectedAnswer === index}
            disabled={isSubmitted}
            onClick={() => setSelectedAnswer(index)}
          >
            <span>{index + 1}</span>
            {option}
          </button>
        ))}
      </div>

      {!isSubmitted ? (
        <button
          type="button"
          className="primary-button quiz-submit-button"
          disabled={selectedAnswer === null}
          onClick={() => { if (selectedAnswer !== null) setIsSubmitted(true) }}
        >
          정답 확인하기 <ArrowRight size={18} />
        </button>
      ) : (
        <>
          <div className={`quiz-feedback ${isCorrect ? 'quiz-feedback-correct' : 'quiz-feedback-wrong'}`} role="status">
            <strong>{isCorrect ? '정답이에요!' : '오답이에요. 해설을 확인해보세요.'}</strong>
            <p>정답: {quiz.answer_index + 1}번 · {quiz.options[quiz.answer_index]}</p>
            <p>{quiz.explanation}</p>
            {isLast && <p>이번 학습에서 {round.length}문제를 모두 풀었어요!</p>}
          </div>
          <button type="button" className="primary-button quiz-submit-button" onClick={nextQuestion}>
            {isLast ? '다시 섞어 풀기' : '다음 문제 풀기'} <ArrowRight size={18} />
          </button>
        </>
      )}
    </article>
  )
}
