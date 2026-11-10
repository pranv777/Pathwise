import { useState } from 'react'
import { adminApi } from '../adminApi'
import { ErrorNote, PageHeader, Pill, Table } from '../ui'
import { fmtDate, useLoad } from '../helpers'

export function Mcp() {
  const servers = useLoad(adminApi.mcp)
  const runs = useLoad(() => adminApi.runs({ kind: 'mcp' }))
  return (
    <>
      <PageHeader
        title="MCP tools"
        sub="Health is inferred from recent tool calls; servers are not pinged."
      >
        <button
          className="btn-secondary"
          onClick={() => {
            servers.reload()
            runs.reload()
          }}
        >
          Refresh
        </button>
      </PageHeader>
      <ErrorNote error={servers.error || runs.error} />
      <div className="grid gap-4 lg:grid-cols-2">
        {servers.data?.map((s) => (
          <section key={s.id} className="panel p-4">
            <div className="flex items-center justify-between">
              <h2 className="font-display text-lg">{s.name}</h2>
              <Pill value={s.health} />
            </div>
            <Table
              rows={s.tools.map((t) => ({ ...t, id: t.name }))}
              cols={[
                {
                  key: 'name',
                  label: 'Tool',
                  render: (t) => <span className="font-mono">{t.name}</span>,
                },
                { key: 'calls_7d', label: 'Calls 7d' },
                { key: 'failed_7d', label: 'Failed' },
                {
                  key: 'avg_ms',
                  label: 'Avg',
                  render: (t) => (t.avg_ms == null ? '—' : `${t.avg_ms} ms`),
                },
              ]}
            />
          </section>
        ))}
      </div>
      <h2 className="mb-3 mt-6 font-display text-lg">Invocation history</h2>
      <div className="panel">
        <Table
          rows={runs.data}
          empty="No MCP calls recorded yet."
          cols={[
            { key: 'at', label: 'When', render: (r) => fmtDate(r.at) },
            { key: 'name', label: 'Tool' },
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

export function Audit() {
  const [action, setAction] = useState('')
  const { data, error } = useLoad(() => adminApi.audit({ action: action || undefined }), [action])
  return (
    <>
      <PageHeader title="Audit log" sub="Every admin mutation and every view of student data." />
      <select
        className="mb-4 rounded border border-hairline bg-panel px-3 py-2 text-sm"
        aria-label="Filter by action"
        value={action}
        onChange={(e) => setAction(e.target.value)}
      >
        <option value="">All actions</option>
        <option value="student">Students</option>
        <option value="drive">Drives</option>
        <option value="kb">Knowledge base</option>
      </select>
      <ErrorNote error={error} />
      <div className="panel">
        <Table
          rows={data}
          empty="No audit entries."
          cols={[
            { key: 'at', label: 'When', render: (r) => fmtDate(r.at) },
            { key: 'admin', label: 'Admin' },
            {
              key: 'action',
              label: 'Action',
              render: (r) => <span className="font-mono">{r.action}</span>,
            },
            { key: 'target', label: 'Target' },
            { key: 'detail', label: 'Detail' },
          ]}
        />
      </div>
    </>
  )
}
