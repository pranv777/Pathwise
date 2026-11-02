import { useState } from 'react'
import { Github, Loader2 } from 'lucide-react'
import api from '../api/client.js'
import { friendlyError } from '../utils/errors.js'

const USERNAME_RE = /^[A-Za-z0-9-]{1,39}$/

const mergeUnique = (existing = [], additions = []) => {
  const seen = new Set(existing.map((s) => s.toLowerCase()))
  const fresh = []
  for (const item of additions) {
    if (item && !seen.has(item.toLowerCase())) {
      seen.add(item.toLowerCase())
      fresh.push(item)
    }
  }
  return fresh
}

export default function GitHubCard({ profile, onProfileChange }) {
  const [username, setUsername] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const analyze = async (e) => {
    e.preventDefault()
    const name = username.trim()
    setNotice('')
    if (!USERNAME_RE.test(name)) {
      setError('Enter a valid GitHub username (letters, numbers and hyphens).')
      return
    }
    setError('')
    setLoading(true)
    try {
      const res = await api.analyzeGithub(name)
      setResult(res.data)
    } catch (err) {
      setResult(null)
      setError(friendlyError(err, 'Could not analyze that GitHub profile.'))
    } finally {
      setLoading(false)
    }
  }

  const addSkills = () => {
    const fresh = mergeUnique(profile.skills, result.top_languages)
    if (fresh.length) onProfileChange({ ...profile, skills: [...profile.skills, ...fresh] })
    setNotice(
      fresh.length ? `Added ${fresh.length} skill(s) to your profile.` : 'Already in your profile.',
    )
  }

  const addProjects = () => {
    const fresh = mergeUnique(profile.projects, result.notable_repos)
    if (fresh.length) onProfileChange({ ...profile, projects: [...profile.projects, ...fresh] })
    setNotice(
      fresh.length
        ? `Added ${fresh.length} project(s) to your profile.`
        : 'Already in your profile.',
    )
  }

  return (
    <div className="panel p-6 space-y-4">
      <div>
        <h2 className="font-display text-xl font-semibold flex items-center gap-2">
          <Github size={18} /> GitHub profile
        </h2>
        <p className="text-sm text-muted mt-1">
          Turn your public repos into skill evidence. We read your languages and top repositories.
        </p>
      </div>

      <form onSubmit={analyze} className="flex gap-2">
        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          maxLength={39}
          placeholder="GitHub username"
          className="flex-1 text-sm px-3 py-2.5 rounded-md border border-hairline focus:border-cobalt outline-none"
        />
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading && <Loader2 size={16} className="animate-spin" />}
          Analyze
        </button>
      </form>

      {error && <p className="text-sm text-signal-red">{error}</p>}

      {result && (
        <div className="space-y-4">
          <p className="text-sm leading-relaxed">{result.summary}</p>

          <div>
            <p className="eyebrow mb-2">Top languages</p>
            <div className="flex flex-wrap gap-1.5">
              {result.top_languages.map((l) => (
                <span
                  key={l}
                  className="text-xs font-mono px-2 py-1 rounded bg-paper border border-hairline"
                >
                  {l}
                </span>
              ))}
            </div>
          </div>

          {result.notable_repos.length > 0 && (
            <div>
              <p className="eyebrow mb-2">Notable repos ({result.public_repos} public)</p>
              <ul className="space-y-1">
                {result.notable_repos.map((r) => (
                  <li key={r} className="text-sm">
                    · {r}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {profile ? (
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={addSkills}
                className="btn-secondary !px-3 !py-1.5 text-xs"
              >
                Add languages to my skills
              </button>
              <button
                type="button"
                onClick={addProjects}
                className="btn-secondary !px-3 !py-1.5 text-xs"
              >
                Add repos to my projects
              </button>
              {notice && <span className="text-xs text-muted">{notice}</span>}
            </div>
          ) : (
            <p className="text-xs text-muted">
              Upload your resume first to add these to your profile.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
