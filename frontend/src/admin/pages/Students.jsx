import { useState } from 'react'
import { adminApi, errMsg } from '../adminApi'
import { ErrorNote, PageHeader, Pill, Table } from '../ui'
import { fmtDate, useLoad } from '../helpers'

export default function Students() {
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState(null)
  const params = { q: q || undefined, status: status || undefined, page, page_size: 20 }
  const { data, error, reload } = useLoad(() => adminApi.students(params), [q, status, page])

  const csvParams = Object.fromEntries(Object.entries({ q, status }).filter(([, v]) => v))
  const pages = data ? Math.max(1, Math.ceil(data.total / 20)) : 1

  return (
    <>
      <PageHeader title="Students" sub="Search, review and manage student accounts.">
        <a className="btn-secondary" href={adminApi.studentsCsvUrl(csvParams)}>
          Export CSV
        </a>
      </PageHeader>
      <div className="mb-4 flex flex-wrap gap-2">
        <input
          className="w-64 rounded border border-hairline bg-panel px-3 py-2 text-sm"
          placeholder="Search name or email"
          aria-label="Search students"
          value={q}
          onChange={(e) => {
            setQ(e.target.value)
            setPage(1)
          }}
        />
        <select
          className="rounded border border-hairline bg-panel px-3 py-2 text-sm"
          aria-label="Filter by status"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value)
            setPage(1)
          }}
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
          <option value="deactivated">Deactivated</option>
        </select>
      </div>
      <ErrorNote error={error} />
      <div className="panel">
        <Table
          rows={data?.items}
          empty="No students match."
          onRow={setSelected}
          cols={[
            { key: 'name', label: 'Name', render: (r) => r.name || '—' },
            { key: 'email', label: 'Email' },
            { key: 'status', label: 'Status', render: (r) => <Pill value={r.status} /> },
            { key: 'created_at', label: 'Joined', render: (r) => fmtDate(r.created_at) },
            { key: 'last_login_at', label: 'Last login', render: (r) => fmtDate(r.last_login_at) },
          ]}
        />
      </div>
      <div className="mt-3 flex items-center justify-between text-sm text-muted">
        <span>{data?.total ?? 0} students</span>
        <div className="flex items-center gap-2">
          <button className="btn-secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            Prev
          </button>
          <span>
            {page} / {pages}
          </span>
          <button
            className="btn-secondary"
            disabled={page >= pages}
            onClick={() => setPage(page + 1)}
          >
            Next
          </button>
        </div>
      </div>
      {selected && (
        <StudentDrawer id={selected.id} onClose={() => setSelected(null)} onChanged={reload} />
      )}
    </>
  )
}

function StudentDrawer({ id, onClose, onChanged }) {
  const { data, error, reload } = useLoad(() => adminApi.student(id), [id])
  const [msg, setMsg] = useState('')

  const change = async (status) => {
    try {
      await adminApi.setStudentStatus(id, status)
      reload()
      onChanged()
    } catch (e) {
      setMsg(errMsg(e))
    }
  }
  const remove = async () => {
    if (!window.confirm('Permanently delete this account and its data? This cannot be undone.'))
      return
    try {
      await adminApi.deleteStudent(id)
      onChanged()
      onClose()
    } catch (e) {
      setMsg(errMsg(e))
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/30" onClick={onClose}>
      <aside
        className="h-full w-full max-w-md overflow-y-auto bg-panel p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Student details"
      >
        <div className="flex items-start justify-between">
          <div>
            <div className="eyebrow">Student</div>
            <h2 className="font-display text-xl">{data?.name || data?.email || 'Loading…'}</h2>
            {data && <div className="text-sm text-muted">{data.email}</div>}
          </div>
          <button className="btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
        <ErrorNote error={error} />
        {msg && (
          <div role="alert" className="mt-3 text-sm text-red-700">
            {msg}
          </div>
        )}
        {data && (
          <div className="mt-5 space-y-5 text-sm">
            <p className="rounded bg-paper p-2 text-xs text-muted">
              Viewing this profile is recorded in the audit log. Resume text is not shown here.
            </p>
            <div className="flex items-center gap-2">
              <Pill value={data.status} />
              {data.status !== 'active' && (
                <button className="btn-secondary" onClick={() => change('active')}>
                  Activate
                </button>
              )}
              {data.status !== 'suspended' && (
                <button className="btn-secondary" onClick={() => change('suspended')}>
                  Suspend
                </button>
              )}
              {data.status !== 'deactivated' && (
                <button className="btn-secondary" onClick={() => change('deactivated')}>
                  Deactivate
                </button>
              )}
            </div>
            <section>
              <div className="eyebrow mb-2">Skills</div>
              {data.skills.length ? (
                <div className="flex flex-wrap gap-1">
                  {data.skills.map((s) => (
                    <span key={s} className="chip">
                      {s}
                    </span>
                  ))}
                </div>
              ) : (
                <span className="text-muted">No parsed skills.</span>
              )}
            </section>
            <section>
              <div className="eyebrow mb-2">Saved jobs ({data.saved_jobs.length})</div>
              <ul className="space-y-1">
                {data.saved_jobs.map((j) => (
                  <li key={j.id} className="flex justify-between">
                    <span>
                      {j.title} {j.company && <span className="text-muted">· {j.company}</span>}
                    </span>
                    <Pill value={j.status} />
                  </li>
                ))}
              </ul>
            </section>
            <section>
              <div className="eyebrow mb-2">Activity history</div>
              <ul className="space-y-1">
                {data.activity.map((a) => (
                  <li key={a.id} className="flex justify-between text-muted">
                    <span className="font-mono">{a.kind}</span>
                    <span>{fmtDate(a.at)}</span>
                  </li>
                ))}
              </ul>
            </section>
            <button className="btn-secondary text-red-700" onClick={remove}>
              Delete account
            </button>
          </div>
        )}
      </aside>
    </div>
  )
}
