import { Loader2, BookOpen } from 'lucide-react'
import { PanelSkeleton } from './Skeleton.jsx'

export default function LearningRoadmap({ skillGap, roadmap, loading, onGenerate }) {
  if (!skillGap || skillGap.missing_skills.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="font-display text-xl font-semibold">Learning Roadmap</h2>
          <p className="text-sm text-muted mt-1">
            Run a skill-gap analysis on a job first — the Learning Recommendation Agent builds a
            roadmap from your missing skills, grounded in the RAG knowledge base.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="font-display text-xl font-semibold">Learning Roadmap</h2>
          <p className="text-sm text-muted mt-1">
            {roadmap ? `~${roadmap.total_estimated_weeks} weeks total` : 'Not generated yet'}
          </p>
        </div>
        <button onClick={onGenerate} className="btn-primary" disabled={loading}>
          {loading ? <Loader2 size={16} className="animate-spin" /> : <BookOpen size={16} />}
          {roadmap ? 'Regenerate' : 'Generate roadmap'}
        </button>
      </div>

      {loading && !roadmap && (
        <PanelSkeleton lines={5} note="Building your roadmap from the knowledge base…" />
      )}
      {roadmap && (
        <div className="space-y-3">
          {roadmap.roadmap.map((item, i) => (
            <div key={i} className="panel p-5 flex gap-4">
              <div className="w-8 h-8 rounded-md bg-cobalt-light flex items-center justify-center shrink-0">
                <span className="font-mono text-xs font-medium text-cobalt-dark">{i + 1}</span>
              </div>
              <div className="flex-1">
                <div className="flex items-baseline justify-between">
                  <h3 className="text-sm font-medium">{item.skill}</h3>
                  <span className="text-xs font-mono text-muted">~{item.estimated_weeks}w</span>
                </div>
                <ul className="mt-2 space-y-1">
                  {item.resources.map((r, j) => (
                    <li key={j} className="text-sm text-ink leading-snug">
                      · {r}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
