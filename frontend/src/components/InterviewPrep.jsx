import { useState } from 'react'
import { PanelSkeleton } from './Skeleton.jsx'
import { Loader2, MessagesSquare, ChevronDown, ChevronUp } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

const CATEGORY_STYLES = {
  technical: 'bg-cobalt-light text-cobalt-dark',
  behavioral: 'bg-signal-amber/10 text-signal-amber',
  system_design: 'bg-signal-green/10 text-signal-green',
}

function QuestionCard({ q, index }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="panel p-5">
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

      <button
        onClick={() => setOpen((o) => !o)}
        className="btn-secondary !px-3 !py-1.5 text-xs mt-3"
      >
        {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        {open ? 'Hide model answer' : 'Show model answer'}
      </button>

      {open && (
        <div className="mt-3 pt-3 border-t border-hairline">
          <p className="eyebrow mb-1.5">Model answer</p>
          <div className="text-sm text-ink leading-relaxed markdown-body">
            <ReactMarkdown>{q.answer}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  )
}

export default function InterviewPrep({ questions, loading, onGenerate, defaultRole }) {
  const [role, setRole] = useState(defaultRole || '')

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-xl font-semibold">Interview Preparation</h2>
        <p className="text-sm text-muted mt-1">
          The Interview Agent generates role-specific questions with model answers, grounded in
          retrieved prep material.
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
          disabled={loading}
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <MessagesSquare size={16} />}
          Generate questions
        </button>
      </div>

      <div className="space-y-3">
        {loading && questions.length === 0 && (
          <PanelSkeleton lines={4} note="Writing role-specific questions…" />
        )}
        {questions.map((q, i) => (
          <QuestionCard key={i} q={q} index={i} />
        ))}
        {questions.length === 0 && !loading && (
          <p className="text-sm text-muted">No questions yet — enter a role above to start.</p>
        )}
      </div>
    </div>
  )
}
