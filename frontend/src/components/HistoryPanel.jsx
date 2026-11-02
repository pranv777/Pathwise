import { useEffect, useState } from 'react'
import { Loader2, RotateCcw } from 'lucide-react'
import api from '../api/client.js'

function progress(p) {
  const done = []
  if (p.match) done.push(`match ${p.match.match_score}`)
  if (p.skill_gap) done.push(`${p.skill_gap.missing_skills.length} gaps`)
  if (p.roadmap) done.push('roadmap')
  if (p.interview_questions?.length) done.push(`${p.interview_questions.length} questions`)
  return done.join(' · ')
}

// SQLite returns naive timestamps ("2026-10-23T10:00:00"), Postgres returns an
// explicit offset ("...+00:00"). Treat naive values as UTC, leave the rest alone.
function parseTimestamp(value) {
  const hasZone = /(Z|[+-]\d{2}:?\d{2})$/i.test(value)
  return new Date(hasZone ? value : `${value}Z`)
}

export default function HistoryPanel({ onRestore }) {
  const [runs, setRuns] = useState(null)

  useEffect(() => {
    api
      .history()
      .then((res) => setRuns(res.data))
      .catch(() => setRuns([]))
  }, [])

  if (runs === null) return <Loader2 className="animate-spin text-muted" size={20} />

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-xl font-semibold">History</h2>
        <p className="text-sm text-muted mt-1">
          Your recent job analyses. Restore one to pick up where you left off.
        </p>
      </div>
      {runs.length === 0 && (
        <p className="text-sm text-muted">Nothing yet. Analyze a job and it will show up here.</p>
      )}
      <div className="space-y-3">
        {runs.map((r) => (
          <div key={r.id} className="panel p-5 flex items-center justify-between gap-4">
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">
                {r.payload.job?.title || 'Analysis'}
                {r.payload.job?.company ? ` · ${r.payload.job.company}` : ''}
              </p>
              <p className="text-xs text-muted mt-0.5">
                {parseTimestamp(r.created_at).toLocaleString()}
                {progress(r.payload) ? ` · ${progress(r.payload)}` : ''}
              </p>
            </div>
            <button
              onClick={() => onRestore(r.payload)}
              className="btn-secondary !px-3 !py-1.5 text-xs shrink-0"
            >
              <RotateCcw size={13} /> Restore
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
