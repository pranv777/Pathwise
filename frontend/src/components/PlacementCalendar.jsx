import { useEffect, useState } from 'react'
import { Bookmark, BookmarkCheck, CalendarPlus, ExternalLink, MapPin } from 'lucide-react'
import api from '../api/client.js'
import { friendlyError } from '../utils/errors.js'
import { downloadDriveIcs, driveToJob } from '../utils/ics.js'

const BRANCHES = ['CSE', 'IT', 'ECE', 'EEE', 'ME', 'CE', 'AI&DS']
const PREFS_KEY = 'wayfind:campus-prefs'
const DEFAULTS = { jobType: 'any', branch: '', cgpa: '', location: '', includePast: false }

function loadPrefs() {
  try {
    return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(PREFS_KEY) || '{}') }
  } catch {
    return DEFAULTS
  }
}

function savePrefs(prefs) {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs))
  } catch {
    /* storage unavailable */
  }
}

const dayParts = (iso) => {
  const d = new Date(`${iso}T00:00:00`)
  return {
    day: d.getDate(),
    month: d.toLocaleString(undefined, { month: 'short' }),
    weekday: d.toLocaleString(undefined, { weekday: 'short' }),
  }
}

export default function PlacementCalendar({ savedIds, onToggleSave }) {
  const [draft, setDraft] = useState(loadPrefs)
  const [applied, setApplied] = useState(draft)
  const [hideIneligible, setHideIneligible] = useState(false)
  const [drives, setDrives] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    const params = {
      job_type: applied.jobType,
      include_past: applied.includePast,
      ...(applied.branch && { branch: applied.branch }),
      ...(applied.cgpa !== '' && { cgpa: applied.cgpa }),
      ...(applied.location.trim() && { location: applied.location.trim() }),
    }
    api
      .campusDrives(params)
      .then((res) => {
        if (!cancelled) {
          setDrives(res.data)
          setError('')
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setDrives([])
          setError(friendlyError(err, 'Could not load placement drives.'))
        }
      })
    return () => {
      cancelled = true
    }
  }, [applied])

  const submit = (e) => {
    e.preventDefault()
    savePrefs(draft)
    setApplied(draft)
  }

  const set = (key) => (e) =>
    setDraft((d) => ({
      ...d,
      [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value,
    }))

  const visible = (drives || []).filter((d) => !(hideIneligible && !d.eligible))
  const checking = applied.branch || applied.cgpa !== ''

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-xl font-semibold">Placement Calendar</h2>
        <p className="text-sm text-muted mt-1">
          Upcoming campus drives. Set your branch and CGPA to see which ones you&apos;re eligible
          for.
        </p>
      </div>

      <form onSubmit={submit} className="panel p-4 grid grid-cols-2 gap-3">
        <label className="text-xs text-muted space-y-1">
          Type
          <select
            value={draft.jobType}
            onChange={set('jobType')}
            className="w-full text-sm px-3 py-2 rounded-md border border-hairline bg-white outline-none focus:border-cobalt"
          >
            <option value="any">Internships & full-time</option>
            <option value="internship">Internship</option>
            <option value="full-time">Full-time</option>
          </select>
        </label>
        <label className="text-xs text-muted space-y-1">
          Branch
          <select
            value={draft.branch}
            onChange={set('branch')}
            className="w-full text-sm px-3 py-2 rounded-md border border-hairline bg-white outline-none focus:border-cobalt"
          >
            <option value="">Not set</option>
            {BRANCHES.map((b) => (
              <option key={b}>{b}</option>
            ))}
          </select>
        </label>
        <label className="text-xs text-muted space-y-1">
          My CGPA (0–10)
          <input
            type="number"
            min="0"
            max="10"
            step="0.01"
            value={draft.cgpa}
            onChange={set('cgpa')}
            placeholder="e.g. 7.8"
            className="w-full text-sm px-3 py-2 rounded-md border border-hairline outline-none focus:border-cobalt"
          />
        </label>
        <label className="text-xs text-muted space-y-1">
          Location
          <input
            value={draft.location}
            onChange={set('location')}
            maxLength={100}
            placeholder="e.g. Bengaluru (remote always shown)"
            className="w-full text-sm px-3 py-2 rounded-md border border-hairline outline-none focus:border-cobalt"
          />
        </label>
        <div className="col-span-2 flex flex-wrap items-center gap-4">
          <button type="submit" className="btn-primary">
            Apply filters
          </button>
          <label className="text-xs text-muted flex items-center gap-1.5">
            <input type="checkbox" checked={draft.includePast} onChange={set('includePast')} />
            Show past drives
          </label>
          <label className="text-xs text-muted flex items-center gap-1.5">
            <input
              type="checkbox"
              checked={hideIneligible}
              onChange={(e) => setHideIneligible(e.target.checked)}
            />
            Hide drives I&apos;m not eligible for
          </label>
        </div>
      </form>

      {error && <p className="text-sm text-signal-red">{error}</p>}
      {drives === null && <p className="text-sm text-muted">Loading drives…</p>}
      {drives && visible.length === 0 && !error && (
        <p className="text-sm text-muted">No drives match these filters.</p>
      )}

      <div className="space-y-3">
        {visible.map((d) => {
          const { day, month, weekday } = dayParts(d.date)
          const saved = savedIds.has(d.id)
          return (
            <div key={d.id} className="panel p-5 flex gap-4">
              <div className="w-14 shrink-0 text-center rounded-md bg-paper border border-hairline py-2">
                <p className="text-[10px] font-mono uppercase text-muted">{month}</p>
                <p className="font-display text-xl font-semibold leading-none my-0.5">{day}</p>
                <p className="text-[10px] text-muted">{weekday}</p>
              </div>

              <div className="flex-1 min-w-0 space-y-2">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="text-sm font-medium">{d.role}</h3>
                    <p className="text-sm text-muted">{d.company}</p>
                  </div>
                  <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-cobalt-light text-cobalt-dark shrink-0">
                    {d.type}
                  </span>
                </div>

                <p className="text-xs text-muted flex flex-wrap items-center gap-x-3 gap-y-1">
                  <span className="flex items-center gap-1">
                    <MapPin size={11} /> {d.location}
                  </span>
                  {d.pay && <span>{d.pay}</span>}
                  <span>Min CGPA {d.min_cgpa ?? '—'}</span>
                  <span>{d.branches.join(', ')}</span>
                </p>

                <p className="text-sm leading-snug">{d.description}</p>

                <div className="flex flex-wrap items-center gap-2 text-xs">
                  {!checking ? (
                    <span className="px-2 py-1 rounded bg-paper text-muted">
                      Set branch & CGPA to check eligibility
                    </span>
                  ) : d.eligible ? (
                    <span className="px-2 py-1 rounded bg-signal-green/10 text-signal-green">
                      You&apos;re eligible
                    </span>
                  ) : (
                    d.reasons.map((r) => (
                      <span key={r} className="px-2 py-1 rounded bg-signal-red/10 text-signal-red">
                        {r}
                      </span>
                    ))
                  )}
                  <span className="text-muted">
                    Apply by {d.apply_by}
                    {d.days_left >= 0 &&
                      ` · ${d.days_left === 0 ? 'today' : `${d.days_left}d to drive`}`}
                  </span>
                </div>

                <div className="flex items-center gap-4 pt-1">
                  <button
                    onClick={() => onToggleSave(driveToJob(d))}
                    className="text-xs text-muted hover:text-cobalt-dark flex items-center gap-1"
                  >
                    {saved ? (
                      <>
                        <BookmarkCheck size={13} className="text-cobalt" /> In tracker
                      </>
                    ) : (
                      <>
                        <Bookmark size={13} /> Add to tracker
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => downloadDriveIcs(d)}
                    className="text-xs text-muted hover:text-cobalt-dark flex items-center gap-1"
                  >
                    <CalendarPlus size={13} /> Add to calendar
                  </button>
                  {d.url && (
                    <a
                      href={d.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-muted hover:text-cobalt-dark flex items-center gap-1"
                    >
                      Details <ExternalLink size={11} />
                    </a>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
