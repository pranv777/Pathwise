import { Loader2, CheckCircle2, XCircle } from 'lucide-react'
import { PanelSkeleton } from './Skeleton.jsx'

function ScoreRing({ score }) {
  const radius = 46
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference
  const color = score >= 70 ? '#15803D' : score >= 40 ? '#B45309' : '#B42318'

  return (
    <svg width="120" height="120" viewBox="0 0 120 120">
      <circle cx="60" cy="60" r={radius} fill="none" stroke="#E3E5E0" strokeWidth="10" />
      <circle
        cx="60"
        cy="60"
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth="10"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 60 60)"
      />
      <text
        x="60"
        y="66"
        textAnchor="middle"
        fontSize="26"
        fontWeight="600"
        fontFamily="Space Grotesk"
        fill="#161A1F"
      >
        {score}
      </text>
    </svg>
  )
}

export default function MatchScore({
  job,
  match = null,
  skillGap = null,
  loading = false,
  onAnalyze,
}) {
  if (!job) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="font-display text-xl font-semibold">Match &amp; Skill Gap</h2>
          <p className="text-sm text-muted mt-1">
            Select a job from Job Search first — the Job Matching and Skill Gap agents need a target
            role to compare your profile against.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="font-display text-xl font-semibold">Match &amp; Skill Gap</h2>
          <p className="text-sm text-muted mt-1">
            {job.title} · {job.company}
          </p>
        </div>
        <button onClick={onAnalyze} className="btn-primary" disabled={loading}>
          {loading ? <Loader2 size={16} className="animate-spin" /> : null}
          {match ? 'Re-analyze' : 'Run analysis'}
        </button>
      </div>

      {loading && !match && (
        <PanelSkeleton
          lines={4}
          note="Comparing your profile with this job. This can take up to 30 seconds."
        />
      )}
      {match && (
        <div className="panel p-6 flex items-center gap-8">
          <ScoreRing score={match.match_score} />
          <div className="flex-1">
            <p className="eyebrow mb-2">Job Matching Agent</p>
            <p className="text-sm text-ink leading-relaxed">{match.rationale}</p>
          </div>
        </div>
      )}

      {match && (
        <div className="grid grid-cols-2 gap-4">
          <div className="panel p-5">
            <p className="eyebrow mb-3 flex items-center gap-1.5">
              <CheckCircle2 size={13} className="text-signal-green" /> Matched skills
            </p>
            <div className="flex flex-wrap gap-1.5">
              {match.matched_skills.map((s, i) => (
                <span
                  key={i}
                  className="text-xs font-mono px-2 py-1 rounded bg-signal-green/10 text-signal-green border border-signal-green/20"
                >
                  {s}
                </span>
              ))}
              {match.matched_skills.length === 0 && (
                <p className="text-xs text-muted">None found</p>
              )}
            </div>
          </div>
          <div className="panel p-5">
            <p className="eyebrow mb-3 flex items-center gap-1.5">
              <XCircle size={13} className="text-signal-red" /> Missing skills
            </p>
            <div className="flex flex-wrap gap-1.5">
              {match.missing_skills.map((s, i) => (
                <span
                  key={i}
                  className="text-xs font-mono px-2 py-1 rounded bg-signal-red/10 text-signal-red border border-signal-red/20"
                >
                  {s}
                </span>
              ))}
              {match.missing_skills.length === 0 && (
                <p className="text-xs text-muted">None — great fit</p>
              )}
            </div>
          </div>
        </div>
      )}

      {skillGap && (
        <div className="panel p-5">
          <p className="eyebrow mb-1">Skill Gap Agent · priority order</p>
          <p className="text-xs text-muted mb-4">{skillGap.explanation}</p>
          <div className="space-y-2">
            {skillGap.priority_order.map((skill, i) => (
              <div key={skill} className="flex items-center gap-3">
                <span className="text-xs font-mono text-muted w-5">{i + 1}</span>
                <div className="flex-1 h-2 rounded-full bg-paper overflow-hidden">
                  <div
                    className="h-full bg-cobalt rounded-full"
                    style={{
                      width: `${100 - i * (80 / Math.max(skillGap.priority_order.length, 1))}%`,
                    }}
                  />
                </div>
                <span className="text-sm w-40 shrink-0">{skill}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
