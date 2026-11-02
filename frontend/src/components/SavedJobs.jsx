import { useState } from 'react'
import { ArrowRight, ExternalLink, MapPin, Trash2 } from 'lucide-react'

const STATUSES = [
  { id: 'saved', label: 'Saved' },
  { id: 'applied', label: 'Applied' },
  { id: 'interview', label: 'Interview' },
  { id: 'offer', label: 'Offer' },
  { id: 'rejected', label: 'Rejected' },
]

const STATUS_STYLE = {
  saved: 'bg-paper text-muted',
  applied: 'bg-cobalt-light text-cobalt-dark',
  interview: 'bg-signal-amber/10 text-signal-amber',
  offer: 'bg-signal-green/10 text-signal-green',
  rejected: 'bg-signal-red/10 text-signal-red',
}

function SavedCard({ item, onUpdate, onRemove, onAnalyze }) {
  const { job } = item
  const [notes, setNotes] = useState(item.notes || '')

  return (
    <div className="panel p-5 space-y-3">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="font-medium text-sm">{job.title}</h3>
          <p className="text-sm text-muted mt-0.5">{job.company}</p>
          {job.location && (
            <p className="text-xs text-muted mt-1 flex items-center gap-1">
              <MapPin size={11} /> {job.location}
            </p>
          )}
        </div>
        <select
          value={item.status}
          onChange={(e) => onUpdate(item.id, { status: e.target.value })}
          aria-label={`Status for ${job.title}`}
          className={`text-xs font-medium px-2.5 py-1.5 rounded-md border border-hairline outline-none ${STATUS_STYLE[item.status]}`}
        >
          {STATUSES.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        onBlur={() => notes !== (item.notes || '') && onUpdate(item.id, { notes })}
        maxLength={2000}
        rows={2}
        placeholder="Notes: referral, interview date, recruiter name…"
        className="w-full text-sm px-3 py-2 rounded-md border border-hairline focus:border-cobalt outline-none resize-y"
      />

      <div className="flex items-center gap-3">
        <button onClick={() => onAnalyze(job)} className="btn-primary !px-3 !py-2 text-xs">
          Analyze match <ArrowRight size={13} />
        </button>
        {job.url && (
          <a
            href={job.url}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-muted hover:text-cobalt-dark flex items-center gap-1"
          >
            View listing <ExternalLink size={11} />
          </a>
        )}
        <button
          onClick={() => onRemove(item.id)}
          className="ml-auto text-xs text-muted hover:text-signal-red flex items-center gap-1"
        >
          <Trash2 size={12} /> Remove
        </button>
      </div>
    </div>
  )
}

export default function SavedJobs({ items, onUpdate, onRemove, onAnalyze, onNavigate }) {
  const [filter, setFilter] = useState('all')
  const visible = filter === 'all' ? items : items.filter((i) => i.status === filter)
  const count = (id) => items.filter((i) => i.status === id).length

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-xl font-semibold">Application Tracker</h2>
        <p className="text-sm text-muted mt-1">
          Bookmark jobs from Job Search or the Placement Calendar, then move them from Saved to
          Applied, Interview and Offer.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {[{ id: 'all', label: 'All' }, ...STATUSES].map((s) => (
          <button
            key={s.id}
            onClick={() => setFilter(s.id)}
            className={`text-xs font-medium px-3 py-1.5 rounded-full border transition-colors ${
              filter === s.id
                ? 'bg-ink text-white border-ink'
                : 'border-hairline text-muted hover:text-ink'
            }`}
          >
            {s.label} ({s.id === 'all' ? items.length : count(s.id)})
          </button>
        ))}
      </div>

      {items.length === 0 ? (
        <div className="panel p-8 text-center">
          <p className="text-sm text-muted">Nothing saved yet.</p>
          <button onClick={() => onNavigate('jobs')} className="btn-primary mt-4">
            Find jobs
          </button>
        </div>
      ) : visible.length === 0 ? (
        <p className="text-sm text-muted">No jobs with this status.</p>
      ) : (
        <div className="space-y-3">
          {visible.map((item) => (
            <SavedCard
              key={item.id}
              item={item}
              onUpdate={onUpdate}
              onRemove={onRemove}
              onAnalyze={onAnalyze}
            />
          ))}
        </div>
      )}
    </div>
  )
}
