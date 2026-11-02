import { useState } from 'react'
import { Loader2, Send, Target, ListChecks, BookOpen, MessageSquare, Sparkles } from 'lucide-react'
import ResumeUpload from './ResumeUpload.jsx'
import { friendlyError } from '../utils/errors.js'
import DeleteDataButton from './DeleteDataButton.jsx'
import StatCard from './StatCard.jsx'
import GitHubCard from './GitHubCard.jsx'
import ReactMarkdown from 'react-markdown'

export default function Overview({
  profile,
  onResumeUploaded,
  onResumeError,
  onProfileChange,
  onDeleteData,
  resumeLoading,
  setResumeLoading,
  match,
  skillGap,
  roadmap,
  interviewQuestions,
  onChat,
  onNavigate,
}) {
  const [chatInput, setChatInput] = useState('')
  const [chatLog, setChatLog] = useState([])
  const [chatLoading, setChatLoading] = useState(false)

  const submitChat = async (e) => {
    e.preventDefault()
    if (!chatInput.trim()) return
    const message = chatInput
    setChatLog((log) => [...log, { role: 'user', text: message }])
    setChatInput('')
    setChatLoading(true)
    try {
      const reply = await onChat(message)
      setChatLog((log) => [...log, { role: 'assistant', text: reply }])
    } catch (err) {
      setChatLog((log) => [...log, { role: 'assistant', text: friendlyError(err) }])
    } finally {
      setChatLoading(false)
    }
  }

  const hasResults = match || skillGap || roadmap || interviewQuestions?.length > 0
  const scoreTone = !match
    ? 'cobalt'
    : match.match_score >= 70
      ? 'green'
      : match.match_score >= 40
        ? 'amber'
        : 'red'

  return (
    <div className="space-y-8">
      <div>
        <p className="eyebrow">Dashboard</p>
        <h1 className="font-display text-2xl font-semibold mt-1">
          {profile?.name
            ? `Welcome back, ${profile.name.split(' ')[0]}`
            : 'Placement & Career Assistant'}
        </h1>
        <p className="text-sm text-muted mt-2 max-w-xl leading-relaxed">
          Upload your resume, then search for a role from the sidebar to get a match score, skill
          gaps, a learning roadmap, and interview prep.
        </p>
      </div>

      {hasResults && (
        <div className="grid grid-cols-4 gap-4">
          <StatCard
            icon={Target}
            label="Match score"
            value={match ? match.match_score : '—'}
            tone={scoreTone}
            onClick={() => onNavigate('match')}
          />
          <StatCard
            icon={ListChecks}
            label="Skill gaps"
            value={skillGap ? skillGap.missing_skills.length : '—'}
            tone={skillGap?.missing_skills.length ? 'amber' : 'green'}
            onClick={() => onNavigate('match')}
          />
          <StatCard
            icon={BookOpen}
            label="Roadmap"
            value={roadmap ? `${roadmap.total_estimated_weeks}w` : '—'}
            tone="cobalt"
            onClick={() => onNavigate('learning')}
          />
          <StatCard
            icon={MessageSquare}
            label="Interview Qs"
            value={interviewQuestions?.length || '—'}
            tone="cobalt"
            onClick={() => onNavigate('interview')}
          />
        </div>
      )}

      <ResumeUpload
        profile={profile}
        onUploaded={onResumeUploaded}
        onError={onResumeError}
        onProfileChange={onProfileChange}
        loading={resumeLoading}
        setLoading={setResumeLoading}
      />

      <GitHubCard profile={profile} onProfileChange={onProfileChange} />

      <div>
        <div className="flex items-center gap-1.5 mb-1">
          <Sparkles size={13} className="text-cobalt" />
          <p className="eyebrow">AI Assistant</p>
        </div>
        <p className="text-xs text-muted mb-4">
          Try `&ldquo;find me jobs in fintech&rdquo;` or `&ldquo;analyze github user
          torvalds&rdquo;`.
        </p>
        <div className="panel p-5">
          <div className="space-y-3 max-h-72 overflow-y-auto mb-4 flex flex-col">
            {chatLog.length === 0 && !chatLoading && (
              <p className="text-sm text-muted py-6 text-center">
                Ask me anything about your job search.
              </p>
            )}
            {chatLog.map((m, i) => (
              <div
                key={i}
                className={
                  m.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant markdown-body'
                }
              >
                {m.role === 'user' ? m.text : <ReactMarkdown>{m.text}</ReactMarkdown>}
              </div>
            ))}
            {chatLoading && (
              <div className="chat-bubble-assistant flex items-center gap-2">
                <Loader2 size={13} className="animate-spin" /> thinking…
              </div>
            )}
          </div>
          <form onSubmit={submitChat} className="flex gap-2">
            <input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              maxLength={2000}
              placeholder="Ask a question…"
              className="flex-1 text-sm px-3 py-2.5 rounded-md border border-hairline focus:border-cobalt outline-none"
            />
            <button type="submit" className="btn-secondary" disabled={chatLoading}>
              <Send size={15} />
            </button>
          </form>
        </div>
      </div>

      <div className="pt-6 border-t border-hairline">
        <DeleteDataButton onDelete={onDeleteData} />
      </div>
    </div>
  )
}
