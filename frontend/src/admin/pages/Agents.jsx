import { useState } from 'react'
import { adminApi } from '../adminApi'
import { ErrorNote, PageHeader, Pill, Table, fmtDate, useLoad } from '../ui'

export default function Agents() {
  const summary = useLoad(adminApi.agents)
  const [name, setName] = useState('')
  const [status, setStatus] = useState('')
  const runs = useLoad(
    () => adminApi.runs({ kind: 'agent', name: name || undefined, status: status || undefined }),
    [name, status],
  )
  const refresh = () => {
    summary.reload()
    runs.reload()
  }

  return (
    <>
      <PageHeader
        title="AI agents"
        sub="Execution metadata only. Prompts, resumes and personal data are never logged."
      >
        <button className="btn-secondary" onClick={refresh}>
          Refresh
        </button>
      </PageHeader>
      <ErrorNote error={summary.error || runs.error} />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {summary.data?.map((a) => (
          <button
            key={a.name}
            onClick={() => setName(name === a.name ? '' : a.name)}
            className={`panel p-4 text-left ${name === a.name ? 'ring-2 ring-cobalt' : ''}`}
          >
            <div className="flex items-center justify-between">
              <span className="font-display text-lg">{a.name}</span>
              <span className="font-mono text-sm text-muted">{a.runs} runs</span>
            </div>
            <div className="mt-2 flex gap-4 text-sm text-muted">
              <span>Success {a.success_rate == null ? '—' : `${a.success_rate}%`}</span>
              <span>Avg {a.avg_ms == null ? '—' : `${a.avg_ms} ms`}</span>
              <span className={a.failed ? 'text-red-700' : ''}>{a.failed} failed</span>
            </div>
            <div className="mt-1 text-xs text-muted">Last: {fmtDate(a.last_run)}</div>
          </button>
        ))}
      </div>
      <div className="mb-3 mt-6 flex items-center gap-2">
        <h2 className="font-display text-lg">Execution history{name && ` · ${name}`}</h2>
        <select
          className="ml-auto rounded border border-hairline bg-panel px-3 py-1.5 text-sm"
          aria-label="Filter by status"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">All</option>
          <option value="success">Success</option>
          <option value="failed">Failed</option>
        </select>
      </div>
      <div className="panel">
        <Table
          rows={runs.data}
          empty="No executions recorded yet. Run a workflow as a student to see them here."
          cols={[
            { key: 'at', label: 'When', render: (r) => fmtDate(r.at) },
            { key: 'name', label: 'Agent' },
            { key: 'status', label: 'Status', render: (r) => <Pill value={r.status} /> },
            { key: 'duration_ms', label: 'Duration', render: (r) => `${r.duration_ms} ms` },
            {
              key: 'error',
              label: 'Error',
              render: (r) => <span className="font-mono text-xs text-red-800">{r.error}</span>,
            },
          ]}
        />
      </div>
    </>
  )
}
