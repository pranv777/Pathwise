import { useState } from 'react'
import { X, Plus } from 'lucide-react'

const MAX_SKILLS = 100

export default function SkillsEditor({ skills = [], onChange }) {
  const [draft, setDraft] = useState('')

  const add = () => {
    const parts = draft
      .split(',')
      .map((s) => s.trim().slice(0, 60))
      .filter(Boolean)
    if (!parts.length) return
    const seen = new Set(skills.map((s) => s.toLowerCase()))
    const next = [...skills]
    for (const p of parts) {
      if (!seen.has(p.toLowerCase()) && next.length < MAX_SKILLS) {
        seen.add(p.toLowerCase())
        next.push(p)
      }
    }
    onChange(next)
    setDraft('')
  }

  const remove = (index) => onChange(skills.filter((_, i) => i !== index))

  return (
    <div>
      <p className="eyebrow mb-2">
        Skills ({skills.length}) — click × to remove, or add missing ones
      </p>
      <div className="flex flex-wrap gap-1.5">
        {skills.map((s, i) => (
          <span
            key={`${s}-${i}`}
            className="inline-flex items-center gap-1 text-xs font-mono pl-2 pr-1 py-1 rounded bg-paper border border-hairline"
          >
            {s}
            <button
              type="button"
              onClick={() => remove(i)}
              aria-label={`Remove ${s}`}
              className="text-muted hover:text-signal-red"
            >
              <X size={12} />
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-2 mt-3">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              add()
            }
          }}
          maxLength={200}
          placeholder="Add skills, comma-separated (e.g. Docker, FastAPI)"
          className="flex-1 text-sm px-3 py-2 rounded-md border border-hairline bg-white focus:outline-none focus:border-cobalt"
        />
        <button
          type="button"
          onClick={add}
          className="inline-flex items-center gap-1 px-3 py-2 rounded-md bg-cobalt text-white text-sm font-medium hover:opacity-90"
        >
          <Plus size={14} /> Add
        </button>
      </div>
    </div>
  )
}
