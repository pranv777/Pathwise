import { useRef, useState } from 'react'
import { adminApi, errMsg } from '../adminApi'
import { ErrorNote, Kpi, PageHeader, Table, useLoad } from '../ui'

const TYPES = [
  ['career_guide', 'Career guide'],
  ['interview_prep', 'Interview prep'],
  ['learning_resource', 'Learning resource'],
  ['job_description', 'Job description'],
]

export default function KnowledgeBase() {
  const { data, error, reload } = useLoad(adminApi.kb)
  const [docType, setDocType] = useState('career_guide')
  const [msg, setMsg] = useState({ text: '', bad: false })
  const [busy, setBusy] = useState(false)
  const fileRef = useRef(null)

  const run = async (fn, ok) => {
    setBusy(true)
    setMsg({ text: '', bad: false })
    try {
      await fn()
      setMsg({ text: ok, bad: false })
      reload()
    } catch (e) {
      setMsg({ text: errMsg(e), bad: true })
    } finally {
      setBusy(false)
    }
  }

  const upload = (e) => {
    e.preventDefault()
    const f = fileRef.current?.files?.[0]
    if (!f) return setMsg({ text: 'Choose a PDF, DOCX, TXT or MD file first.', bad: true })
    run(async () => {
      await adminApi.kbUpload(docType, f)
      fileRef.current.value = ''
    }, `Indexed ${f.name}. Uploading the same name replaces the old version.`)
  }

  return (
    <>
      <PageHeader
        title="Knowledge base"
        sub="Shared documents the agents retrieve from. Student resumes are never listed here."
      >
        <button
          className="btn-secondary"
          disabled={busy}
          onClick={() =>
            window.confirm('Re-run the seed ingestion?') &&
            run(adminApi.kbReseed, 'Seed ingestion finished.')
          }
        >
          Re-seed
        </button>
      </PageHeader>
      <ErrorNote error={error} />
      <div className="grid grid-cols-2 gap-4 sm:max-w-md">
        <Kpi label="Documents" value={data?.documents} />
        <Kpi label="Chunks" value={data?.chunks} />
      </div>
      <form onSubmit={upload} className="panel mt-6 flex flex-wrap items-end gap-3 p-4">
        <label className="text-sm">
          Type
          <select
            className="mt-1 block rounded border border-hairline bg-panel px-3 py-2"
            value={docType}
            onChange={(e) => setDocType(e.target.value)}
          >
            {TYPES.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          File (PDF, DOCX, TXT, MD)
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.docx,.txt,.md"
            className="mt-1 block text-sm"
          />
        </label>
        <button className="btn-primary" disabled={busy}>
          Upload
        </button>
        {msg.text && (
          <span role="status" className={`text-sm ${msg.bad ? 'text-red-700' : 'text-green-700'}`}>
            {msg.text}
          </span>
        )}
      </form>
      <div className="panel mt-6">
        <Table
          rows={data?.items?.map((d) => ({ ...d, id: d.source }))}
          empty="No shared documents indexed."
          cols={[
            { key: 'source', label: 'Source' },
            { key: 'doc_type', label: 'Type' },
            { key: 'chunks', label: 'Chunks' },
            {
              key: 'act',
              label: '',
              render: (r) => (
                <button
                  className="btn-secondary text-red-700"
                  disabled={busy}
                  onClick={() =>
                    window.confirm(`Delete ${r.source}?`) &&
                    run(() => adminApi.kbDelete(r.source), `Deleted ${r.source}.`)
                  }
                >
                  Delete
                </button>
              ),
            },
          ]}
        />
      </div>
    </>
  )
}
