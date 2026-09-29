export type Quiz = {
  id: string
  question: string
  options: string[]
  answer_index: number
  explanation: string
}

// Shuffle questions, not options: each answer index stays attached to its question.
export function createQuizRound<T extends { id: string }>(
  quizzes: readonly T[],
  previousId?: string,
  random: () => number = Math.random,
): T[] {
  const round = [...quizzes]
  for (let i = round.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1))
    ;[round[i], round[j]] = [round[j], round[i]]
  }
  // A fresh round must not immediately repeat the question just answered.
  if (round.length > 1 && round[0].id === previousId) {
    const next = 1 + Math.floor(random() * (round.length - 1))
    ;[round[0], round[next]] = [round[next], round[0]]
  }
  return round
}
