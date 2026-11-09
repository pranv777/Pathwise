import { useState } from 'react'
import { adminApi, errMsg } from '../adminApi'
import { ErrorNote, PageHeader, Pill, Table, useLoad } from '../ui'

const blank = {
  company: '',
  role: '',
  type: 'full-time',
  date: '',
  apply_by: '',
  location: '',
  branches: '',
  min_cgpa: '',
  pay: '',
  url: '',
  description: '',
}

const today = new Date().toISOString().slice(0, 10)

export default function Drives() {
  const { data, error, reload } = useLoad(adminApi.drives)
  const [form, setForm] = useState(null)
  const [msg, setMsg] = useState('')

  const edit = (d) =>
    setForm({
      ...blank,
      ...d,
      branches: (d.branches || []).join(', '),
      min_cgpa: d.min_cgpa ?? '',
      apply_by: d.apply_by ?? '',
    })

  const save = async (e) => {
    e.preventDefault()
    setMsg('')
    const body = {
      ...form,
      min_cgpa: form.min_cgpa === '' ? null : Number(form.min_cgpa),
      apply_by: form.apply_by || null,
      branches: form.branches
        .split(',')
        .map((b) => b.trim())
        .filter(Boolean),
    }
    try {
      await adminApi.saveDrive(body)
      setForm(null)
      reload()
    } catch (err) {
      setMsg(errMsg(err))
    }
  }
  const remove = async (d) => {
    if (!window.confirm(`Delete the ${d.company} drive?`)) return
    try {
      await adminApi.deleteDrive(d.id)
      reload()
    } catch (err) {
      setMsg(errMsg(err))
    }
  }
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const input = 'w-full rounded border border-hairline bg-panel px-3 py-2 text-sm'
  return (
    <>
      <PageHeader
        title="Campus drives"
        sub="Companies, eligibility and deadlines shown to students."
      >
        <button className="btn-primary" onClick={() => setForm({ ...blank })}>
          New drive
        </button>
      </PageHeader>
      <ErrorNote error={error} />
      {msg && (
        <div role="alert" className="mb-3 text-sm text-red-700">
          {msg}
        </div>
      )}
      <div className="panel">
        <Table
          rows={data}
          empty="No drives yet."
          cols={[
            { key: 'company', label: 'Company', render: (r) => <>{r.company}</> },
            { key: 'role', label: 'Role' },
            { key: 'date', label: 'Drive date' },
            { key: 'apply_by', label: 'Apply by', render: (r) => r.apply_by || '—' },
            { key: 'min_cgpa', label: 'Min CGPA', render: (r) => r.min_cgpa ?? '—' },
            {
              key: 'state',
              label: 'State',
              render: (r) => <Pill value={r.date >= today ? 'active' : 'expired'} />,
            },
            {
              key: 'act',
              label: '',
              render: (r) => (
                <span className="flex gap-2">
                  <button className="btn-secondary" onClick={() => edit(r)}>
                    Edit
                  </button>
                  <button className="btn-secondary text-red-700" onClick={() => remove(r)}>
                    Delete
                  </button>
                </span>
              ),
            },
          ]}
        />
      </div>
      {form && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 p-4">
          <form
            onSubmit={save}
            className="panel max-h-full w-full max-w-lg space-y-3 overflow-y-auto bg-panel p-5"
          >
            <h2 className="font-display text-xl">{form.id ? 'Edit drive' : 'New drive'}</h2>
            <label className="block text-sm">
              Company
              <input required className={input} value={form.company} onChange={set('company')} />
            </label>
            <label className="block text-sm">
              Role
              <input className={input} value={form.role} onChange={set('role')} />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="block text-sm">
                Type
                <select className={input} value={form.type} onChange={set('type')}>
                  <option value="full-time">Full-time</option>
                  <option value="internship">Internship</option>
                </select>
              </label>
              <label className="block text-sm">
                Location
                <input className={input} value={form.location} onChange={set('location')} />
              </label>
              <label className="block text-sm">
                Drive date
                <input
                  required
                  type="date"
                  className={input}
                  value={form.date}
                  onChange={set('date')}
                />
              </label>
              <label className="block text-sm">
                Apply by
                <input
                  type="date"
                  className={input}
                  value={form.apply_by}
                  onChange={set('apply_by')}
                />
              </label>
              <label className="block text-sm">
                Min CGPA
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="10"
                  className={input}
                  value={form.min_cgpa}
                  onChange={set('min_cgpa')}
                />
              </label>
              <label className="block text-sm">
                Pay
                <input className={input} value={form.pay} onChange={set('pay')} />
              </label>
            </div>
            <label className="block text-sm">
              Eligible branches (comma separated, or All)
              <input className={input} value={form.branches} onChange={set('branches')} />
            </label>
            <label className="block text-sm">
              Apply URL
              <input type="url" className={input} value={form.url} onChange={set('url')} />
            </label>
            <label className="block text-sm">
              Description
              <textarea
                rows={3}
                className={input}
                value={form.description}
                onChange={set('description')}
              />
            </label>
            <div className="flex justify-end gap-2">
              <button type="button" className="btn-secondary" onClick={() => setForm(null)}>
                Cancel
              </button>
              <button className="btn-primary">Save</button>
            </div>
          </form>
        </div>
      )}
    </>
  )
}
