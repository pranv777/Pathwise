import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/client.js', () => ({ default: { evaluateAnswer: vi.fn() } }))

import api from '../api/client.js'
import InterviewPrep from './InterviewPrep'

const QUESTIONS = [
  { question: 'What is a hash map?', category: 'technical', answer: 'A **table** of pairs.' },
  { question: 'Tell me about a conflict.', category: 'behavioral', answer: 'Use STAR.' },
]

function Harness({ questions = QUESTIONS, loading = false, onGenerate = vi.fn(), role = '' }) {
  const [answers, setAnswers] = useState([])
  const [results, setResults] = useState([])
  return (
    <InterviewPrep
      questions={questions}
      loading={loading}
      onGenerate={onGenerate}
      defaultRole={role}
      answers={answers}
      setAnswers={setAnswers}
      results={results}
      setResults={setResults}
    />
  )
}

const ok = (score) =>
  /** @type {any} */ ({
    data: { score, feedback: `fb ${score}`, improved_answer_tips: ['tip a', 'tip b'] },
  })

async function answerAll(user) {
  await user.type(screen.getByLabelText('Your answer to question 1'), 'my first')
  await user.type(screen.getByLabelText('Your answer to question 2'), 'my second')
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.evaluateAnswer).mockResolvedValue(ok(8))
})

describe('InterviewPrep: generating', () => {
  it('shows an empty state and a skeleton while loading', () => {
    const { rerender } = render(<Harness questions={[]} />)
    expect(screen.getByText(/No questions yet/)).toBeInTheDocument()
    rerender(<Harness questions={[]} loading />)
    expect(screen.queryByText(/No questions yet/)).not.toBeInTheDocument()
  })

  it('generates only when a role is entered', async () => {
    const onGenerate = vi.fn()
    const user = userEvent.setup()
    render(<Harness questions={[]} onGenerate={onGenerate} />)
    await user.click(screen.getByRole('button', { name: /Generate questions/ }))
    expect(onGenerate).not.toHaveBeenCalled()
    await user.type(screen.getByPlaceholderText(/Target role/), 'Backend Intern')
    await user.click(screen.getByRole('button', { name: /Generate questions/ }))
    expect(onGenerate).toHaveBeenCalledWith('Backend Intern')
  })

  it('prefills the role', () => {
    render(<Harness questions={[]} role="Data Analyst" />)
    expect(screen.getByPlaceholderText(/Target role/)).toHaveValue('Data Analyst')
  })
})

describe('InterviewPrep: answering and scoring', () => {
  it('needs every question answered before submitting', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    const submit = screen.getByRole('button', { name: /Submit answers/ })
    expect(submit).toBeDisabled()
    expect(screen.getByText(/0 of 2 answered/)).toBeInTheDocument()
    await user.type(screen.getByLabelText('Your answer to question 1'), 'abc')
    expect(screen.getByText(/1 of 2 answered/)).toBeInTheDocument()
    expect(screen.getByText('3/10000')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Your answer to question 2'), 'def')
    expect(submit).toBeEnabled()
  })

  it('scores each answer and shows feedback, tips, model answer and the average', async () => {
    vi.mocked(api.evaluateAnswer).mockResolvedValueOnce(ok(8)).mockResolvedValueOnce(ok(3))
    const user = userEvent.setup()
    render(<Harness role="Dev" />)
    await answerAll(user)
    await user.click(screen.getByRole('button', { name: /Submit answers/ }))
    expect(await screen.findByText('fb 8')).toBeInTheDocument()
    expect(screen.getByText('fb 3')).toBeInTheDocument()
    expect(screen.getAllByText('tip a')).toHaveLength(2)
    expect(screen.getByText('table')).toBeInTheDocument()
    expect(screen.getByText(/5\.5 \/ 10/)).toBeInTheDocument()
    expect(screen.getByText('(2 of 2 scored)')).toBeInTheDocument()
    expect(api.evaluateAnswer).toHaveBeenCalledWith('What is a hash map?', 'my first', 'Dev')
    expect(screen.getByLabelText('Your answer to question 1')).toBeDisabled()
  })

  it.each([
    [9, 'text-signal-green'],
    [5, 'text-signal-amber'],
    [2, 'text-signal-red'],
  ])('colours a score of %i', async (score, tone) => {
    vi.mocked(api.evaluateAnswer).mockResolvedValue(ok(score))
    const user = userEvent.setup()
    render(<Harness questions={[QUESTIONS[0]]} />)
    await user.type(screen.getByLabelText('Your answer to question 1'), 'x')
    await user.click(screen.getByRole('button', { name: /Submit answers/ }))
    expect(await screen.findByText(String(score), { selector: 'span' })).toHaveClass(tone)
  })

  it('lets one failed question be retried without losing the others', async () => {
    vi.mocked(api.evaluateAnswer)
      .mockResolvedValueOnce(ok(8))
      .mockRejectedValueOnce(new Error('x'))
      .mockResolvedValueOnce(ok(6))
    const user = userEvent.setup()
    render(<Harness />)
    await answerAll(user)
    await user.click(screen.getByRole('button', { name: /Submit answers/ }))
    expect(await screen.findByText('Could not score this answer.')).toBeInTheDocument()
    expect(screen.getByText('fb 8')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Retry scoring' }))
    expect(await screen.findByText('fb 6')).toBeInTheDocument()
    expect(screen.queryByText('Could not score this answer.')).not.toBeInTheDocument()
  })

  it('does not show an average when nothing could be scored', async () => {
    vi.mocked(api.evaluateAnswer).mockRejectedValue(new Error('x'))
    const user = userEvent.setup()
    render(<Harness questions={[QUESTIONS[0]]} />)
    await user.type(screen.getByLabelText('Your answer to question 1'), 'x')
    await user.click(screen.getByRole('button', { name: /Submit answers/ }))
    await screen.findByText('Could not score this answer.')
    expect(screen.queryByText(/Average score/)).not.toBeInTheDocument()
  })

  it('omits the tips section when there are none', async () => {
    vi.mocked(api.evaluateAnswer).mockResolvedValue(
      /** @type {any} */ ({ data: { score: 7, feedback: 'solid', improved_answer_tips: [] } }),
    )
    const user = userEvent.setup()
    render(<Harness questions={[QUESTIONS[0]]} />)
    await user.type(screen.getByLabelText('Your answer to question 1'), 'x')
    await user.click(screen.getByRole('button', { name: /Submit answers/ }))
    await screen.findByText('solid')
    expect(screen.queryByText('How to improve')).not.toBeInTheDocument()
  })

  it('resets everything with Try again', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    await answerAll(user)
    await user.click(screen.getByRole('button', { name: /Submit answers/ }))
    await user.click(await screen.findByRole('button', { name: /Try again/ }))
    await waitFor(() => expect(screen.getByLabelText('Your answer to question 1')).toBeEnabled())
    expect(screen.getByLabelText('Your answer to question 1')).toHaveValue('')
    expect(screen.getByRole('button', { name: /Submit answers/ })).toBeDisabled()
  })

  it('renders an unknown category with a neutral style', () => {
    render(<Harness questions={[{ question: 'Q?', category: 'other', answer: 'A' }]} />)
    expect(screen.getByText('other')).toHaveClass('text-muted')
  })
})
