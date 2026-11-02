import { useState } from 'react'
import { PanelSkeleton } from './Skeleton.jsx'
import {
  Search,
  Loader2,
  MapPin,
  ExternalLink,
  ArrowRight,
  Bookmark,
  BookmarkCheck,
} from 'lucide-react'

export default function JobSearch({
  onSearch,
  jobs,
  toolUsed,
  onSelectJob,
  selectedJobId,
  loading,
  savedIds,
  onToggleSave,
}) {
  const [query, setQuery] = useState('')
  const [location, setLocation] = useState('')
  const [jobType, setJobType] = useState('any')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!query.trim()) return
    onSearch(query, location, jobType)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-xl font-semibold">Job Search</h2>
        <p className="text-sm text-muted mt-1">
          The Orchestrator calls the job-search MCP tool — live web search when configured,
          otherwise a curated local listings set.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="panel p-4 flex gap-3">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          maxLength={200}
          placeholder="e.g. backend engineer intern, python"
          className="flex-1 text-sm px-3 py-2.5 rounded-md border border-hairline focus:border-cobalt outline-none"
        />
        <input
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          maxLength={100}
          placeholder="Location (optional)"
          className="w-48 text-sm px-3 py-2.5 rounded-md border border-hairline focus:border-cobalt outline-none"
        />
        <select
          value={jobType}
          onChange={(e) => setJobType(e.target.value)}
          aria-label="Job type"
          className="text-sm px-3 py-2.5 rounded-md border border-hairline focus:border-cobalt outline-none bg-white"
        >
          <option value="any">Any type</option>
          <option value="internship">Internship</option>
          <option value="full-time">Full-time</option>
        </select>
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
          Search
        </button>
      </form>

      {toolUsed && (
        <p className="text-xs font-mono text-muted">
          tool_used: <span className="text-cobalt-dark">{toolUsed}</span>
        </p>
      )}

      <div className="space-y-3">
        {loading ? (
          <PanelSkeleton lines={3} note="Searching for roles…" />
        ) : (
          jobs.map((job) => {
            const isSelected = selectedJobId === job.id
            return (
              <div
                key={job.id}
                className={`panel p-5 transition-colors ${isSelected ? 'border-cobalt ring-1 ring-cobalt' : ''}`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="font-medium text-sm">{job.title}</h3>
                    <p className="text-sm text-muted mt-0.5">{job.company}</p>
                    {job.location && (
                      <p className="text-xs text-muted mt-1 flex items-center gap-1">
                        <MapPin size={11} /> {job.location}
                      </p>
                    )}
                  </div>
                  <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-paper border border-hairline text-muted shrink-0">
                    {job.source}
                  </span>
                </div>
                <p className="text-sm text-ink leading-relaxed mt-3 line-clamp-3">
                  {job.description}
                </p>
                <div className="flex items-center gap-3 mt-4">
                  <button
                    onClick={() => onSelectJob(job)}
                    className="btn-primary !px-3 !py-2 text-xs"
                  >
                    {isSelected ? 'Selected for matching' : 'Analyze this job'}
                    <ArrowRight size={13} />
                  </button>
                  <button
                    onClick={() => onToggleSave(job)}
                    className="text-xs text-muted hover:text-cobalt-dark flex items-center gap-1"
                  >
                    {savedIds.has(job.id) ? (
                      <>
                        <BookmarkCheck size={13} className="text-cobalt" /> Saved
                      </>
                    ) : (
                      <>
                        <Bookmark size={13} /> Save
                      </>
                    )}
                  </button>
                  {job.url && job.url !== '' && (
                    <a
                      href={job.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-muted hover:text-cobalt-dark flex items-center gap-1"
                    >
                      View listing <ExternalLink size={11} />
                    </a>
                  )}
                </div>
              </div>
            )
          })
        )}
        {jobs.length === 0 && !loading && (
          <p className="text-sm text-muted">No results yet — try a search above.</p>
        )}
      </div>
    </div>
  )
}
