import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Loader2, MessagesSquare, Send, RotateCcw } from 'lucide-react'
import api from '../api/client.js'
import { friendlyError } from '../utils/errors.js'
import { PanelSkeleton } from './Skeleton.jsx'

const MAX_ANSWER = 10000

const CATEGORY_STYLES = {
  technical: 'bg-cobalt-light text-cobalt-dark',
  behavioral: 'bg-signal-amber/10 text-signal-amber',
  system_design: 'bg-signal-green/10 text-signal-green',
}

const scoreTone = (score) =>
  score >= 7 ? 'text-signal-green' : score >= 4 ? 'text-signal-amber' : 'text-signal-red'

function Feedback({ q, result, onRetry }) {
  return (
    <div className="space-y-3 pt-3 border-t border-hairline">
      {result === null && (
        <p className="text-sm text-muted flex items-center gap-2">
          <Loader2 size={14} className="animate-spin" /> Scoring your answer…
        </p>
      )}

      {result?.status === 'error' && (
        <div className="text-sm">
          <p className="text-signal-red">{result.message}</p>
          <button onClick={onRetry} className="btn-secondary !px-3 !py-1.5 text-xs mt-2">
            Retry scoring
          </button>
        </div>
      )}

      {result?.status === 'ok' && (
        <>
          <p className="font-display text-2xl font-semibold">
            <span className={scoreTone(result.score)}>{result.score}</span>
            <span className="text-muted text-base"> / 10</span>
          </p>
          <div>
            <p className="eyebrow mb-1.5">Feedback</p>
            <p className="text-sm leading-relaxed">{result.feedback}</p>
          </div>
          {result.improved_answer_tips?.length > 0 && (
            <div>
              <p className="eyebrow mb-1.5">How to improve</p>
              <ul className="list-disc pl-5 text-sm space-y-1">
                {result.improved_answer_tips.map((tip, i) => (
                  <li key={i}>{tip}</li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      <div>
        <p className="eyebrow mb-1.5">Model answer</p>
        <div className="text-sm text-ink leading-relaxed markdown-body">
          <ReactMarkdown>{q.answer}</ReactMarkdown>
        </div>
      </div>
    </div>
  )
}

function QuestionCard({ q, index, answer, onChange, submitted, result, onRetry }) {
  return (
    <div className="panel p-5 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium leading-snug">
          <span className="font-mono text-muted mr-2">{index + 1}.</span>
          {q.question}
        </p>
        <span
          className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded shrink-0 ${CATEGORY_STYLES[q.category] || 'bg-paper text-muted'}`}
        >
          {q.category}
        </span>
      </div>

      <textarea
        aria-label={`Your answer to question ${index + 1}`}
        value={answer}
        onChange={(e) => onChange(e.target.value)}
        disabled={submitted}
        maxLength={MAX_ANSWER}
        rows={5}
        placeholder="Type or paste your answer here…"
        className="w-full text-sm px-3 py-2.5 rounded-md border border-hairline focus:border-cobalt outline-none disabled:bg-paper disabled:text-muted"
      />
      {!submitted && (
        <p className="text-[11px] font-mono text-muted text-right">
          {answer.length}/{MAX_ANSWER}
        </p>
      )}

      {submitted && <Feedback q={q} result={result} onRetry={onRetry} />}
    </div>
  )
}

export default function InterviewPrep({
  questions,
  loading,
  onGenerate,
  defaultRole,
  answers,
  setAnswers,
  results,
  setResults,
}) {
  const [role, setRole] = useState(defaultRole || '')
  const [submitting, setSubmitting] = useState(false)

  const answerAt = (i) => answers[i] ?? ''
  const submitted = results.length > 0
  const answeredCount = questions.filter((_, i) => answerAt(i).trim()).length
  const allAnswered = questions.length > 0 && answeredCount === questions.length

  const setAnswer = (i, value) =>
    setAnswers((prev) => {
      const next = questions.map((_, j) => prev[j] ?? '')
      next[i] = value
      return next
    })

  const putResult = (i, value) =>
    setResults((prev) => {
      const next = questions.map((_, j) => prev[j] ?? null)
      next[i] = value
      return next
    })

  // Never rejects: a failed question becomes an error result with its own Retry button.
  const evaluateOne = async (i) => {
    try {
      const res = await api.evaluateAnswer(questions[i].question, answerAt(i).trim(), role.trim())
      return { status: 'ok', ...res.data }
    } catch (err) {
      return { status: 'error', message: friendlyError(err, 'Could not score this answer.') }
    }
  }

  const submit = async () => {
    setSubmitting(true)
    setResults(questions.map(() => null))
    await Promise.all(questions.map(async (_, i) => putResult(i, await evaluateOne(i))))
    setSubmitting(false)
  }

  const retry = async (i) => {
    putResult(i, null)
    putResult(i, await evaluateOne(i))
  }

  const practiceAgain = () => {
    setAnswers([])
    setResults([])
  }

  const scored = results.filter((r) => r?.status === 'ok')
  const finished = submitted && results.every(Boolean)
  const average = scored.length
    ? (scored.reduce((sum, r) => sum + r.score, 0) / scored.length).toFixed(1)
    : null

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-xl font-semibold">Interview Preparation</h2>
        <p className="text-sm text-muted mt-1">
          Generate role-specific questions, answer all of them, then submit to get a score, feedback
          and a model answer for each one.
        </p>
      </div>

      <div className="panel p-4 flex gap-3">
        <input
          value={role}
          onChange={(e) => setRole(e.target.value)}
          maxLength={200}
          placeholder="Target role, e.g. Backend Engineer Intern"
          className="flex-1 text-sm px-3 py-2.5 rounded-md border border-hairline focus:border-cobalt outline-none"
        />
        <button
          onClick={() => role.trim() && onGenerate(role)}
          className="btn-primary"
          disabled={loading || submitting}
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <MessagesSquare size={16} />}
          Generate questions
        </button>
      </div>

      {finished && average && (
        <div className="panel p-4 flex items-center justify-between">
          <p className="text-sm">
            Average score: <span className="font-semibold">{average} / 10</span>
            <span className="text-muted">
              {' '}
              ({scored.length} of {questions.length} scored)
            </span>
          </p>
          <button onClick={practiceAgain} className="btn-secondary !px-3 !py-1.5 text-xs">
            <RotateCcw size={13} /> Try again
          </button>
        </div>
      )}

      <div className="space-y-3">
        {loading && questions.length === 0 && (
          <PanelSkeleton lines={4} note="Writing role-specific questions…" />
        )}
        {questions.map((q, i) => (
          <QuestionCard
            key={i}
            q={q}
            index={i}
            answer={answerAt(i)}
            onChange={(value) => setAnswer(i, value)}
            submitted={submitted}
            result={results[i] ?? null}
            onRetry={() => retry(i)}
          />
        ))}
        {questions.length === 0 && !loading && (
          <p className="text-sm text-muted">No questions yet — enter a role above to start.</p>
        )}
      </div>

      {questions.length > 0 && !submitted && (
        <div className="flex items-center gap-3">
          <button onClick={submit} className="btn-primary" disabled={!allAnswered || submitting}>
            {submitting ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            Submit answers
          </button>
          <p className="text-xs text-muted">
            {answeredCount} of {questions.length} answered
            {!allAnswered && ' — answer every question to submit'}
          </p>
        </div>
      )}
    </div>
  )
}
