import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createQuizRound } from '../src/quiz.ts'

const bank = Object.freeze(Array.from({ length: 5 }, (_, i) => Object.freeze({
  id: `concept-${i}`, question: `Question ${i}`,
  options: [`A${i}`, `B${i}`, `C${i}`, `D${i}`], answer_index: i % 4,
  explanation: `Explanation ${i}`,
})))

test('every round includes all five questions once without changing answer/explanation pairing', () => {
  for (const random of [() => 0, () => 0.25, () => 0.5, () => 0.99999]) {
    const round = createQuizRound(bank, undefined, random)
    assert.equal(new Set(round.map(q => q.id)).size, 5)
    assert.deepEqual(round.map(q => q.id).sort(), bank.map(q => q.id).sort())
    for (const quiz of round) assert.equal(quiz, bank.find(q => q.id === quiz.id))
  }
  assert.deepEqual(bank.map(q => q.id), ['concept-0', 'concept-1', 'concept-2', 'concept-3', 'concept-4'])
})

test('shuffle uses random values and a new round never starts with the previous last question', () => {
  assert.notDeepEqual(createQuizRound(bank, undefined, () => 0), createQuizRound(bank, undefined, () => 0.99999))
  for (const previous of bank) {
    for (const sample of [0, 0.25, 0.5, 0.99999]) {
      const round = createQuizRound(bank, previous.id, () => sample)
      assert.notEqual(round[0].id, previous.id)
      assert.equal(new Set(round.map(q => q.id)).size, 5)
    }
  }
})

test('empty and single-question banks are handled without looping or dropping a question', () => {
  assert.deepEqual(createQuizRound([]), [])
  assert.deepEqual(createQuizRound([bank[0]], bank[0].id), [bank[0]])
})
