import { useEffect, useRef, useState } from 'react'
import { useAuth } from './context/useAuth.js'
import LoginPage from './components/LoginPage.jsx'
import Sidebar from './components/Sidebar.jsx'
import Overview from './components/Overview.jsx'
import JobSearch from './components/JobSearch.jsx'
import MatchScore from './components/MatchScore.jsx'
import LearningRoadmap from './components/LearningRoadmap.jsx'
import InterviewPrep from './components/InterviewPrep.jsx'
import HistoryPanel from './components/HistoryPanel.jsx'
import NextStep from './components/NextStep.jsx'
import SavedJobs from './components/SavedJobs.jsx'
import PlacementCalendar from './components/PlacementCalendar.jsx'
import ServerWakeBanner from './components/ServerWakeBanner.jsx'
import api from './api/client.js'
import { friendlyError } from './utils/errors.js'

export default function App() {
  const { user, loading, logout } = useAuth()

  let content
  if (loading) {
    content = (
      <div className="h-screen flex items-center justify-center text-sm text-muted">Loading…</div>
    )
  } else if (!user) {
    content = <LoginPage />
  } else {
    // key={user.id}: a different user gets a brand-new Dashboard, so no state leaks across accounts.
    content = <Dashboard key={user.id} user={user} onLogout={logout} />
  }

  return (
    <>
      <ServerWakeBanner />
      {content}
    </>
  )
}

function Dashboard({ user, onLogout }) {
  const sessionIdRef = useRef(
    sessionStorage.getItem('chat_session_id') ||
      (() => {
        const id = crypto.randomUUID()
        sessionStorage.setItem('chat_session_id', id)
        return id
      })(),
  )

  const [activeTab, setActiveTab] = useState('overview')
  const [profile, setProfile] = useState(null)
  const [jobs, setJobs] = useState([])
  const [toolUsed, setToolUsed] = useState('')
  const [selectedJob, setSelectedJob] = useState(null)
  const [match, setMatch] = useState(null)
  const [skillGap, setSkillGap] = useState(null)
  const [roadmap, setRoadmap] = useState(null)
  const [interviewQuestions, setInterviewQuestions] = useState([])
  const [error, setError] = useState('')

  const [resumeLoading, setResumeLoading] = useState(false)
  const [jobSearchLoading, setJobSearchLoading] = useState(false)
  const [matchLoading, setMatchLoading] = useState(false)
  const [roadmapLoading, setRoadmapLoading] = useState(false)
  const [interviewLoading, setInterviewLoading] = useState(false)

  // Restore the saved profile so returning users don't have to re-upload.
  useEffect(() => {
    api
      .getProfile()
      .then((res) => setProfile((current) => current ?? res.data.profile))
      .catch(() => {})
  }, [])

  const [savedJobs, setSavedJobs] = useState([])

  useEffect(() => {
    api
      .savedJobs()
      .then((res) => setSavedJobs(res.data))
      .catch(() => {})
  }, [])

  const savedIds = new Set(savedJobs.map((s) => s.job.id))

  const changeTab = (tab) => {
    setError('')
    setActiveTab(tab)
  }

  const handleResumeUpload = async (file) => {
    const res = await api.uploadResume(file) // backend also saves the profile
    setProfile(res.data.profile)
  }

  // Called when the user adds/removes skills in the profile editor.
  const handleProfileChange = (next) => {
    setProfile(next)
    api.saveProfile(next).catch(() => setError('Could not save your profile changes.'))
  }

  const handleDeleteData = async () => {
    await api.deleteMyData()
    setProfile(null)
    setJobs([])
    setToolUsed('')
    setSelectedJob(null)
    setMatch(null)
    setSkillGap(null)
    setRoadmap(null)
    setInterviewQuestions([])
    setError('')
    setActiveTab('overview')
    setSavedJobs([])
  }

  const handleJobSearch = async (query, location, jobType) => {
    setJobSearchLoading(true)
    try {
      const res = await api.searchJobs(query, location, 5, jobType)
      setJobs(res.data.jobs)
      setToolUsed(res.data.tool_used)
    } catch (err) {
      setError(friendlyError(err, 'Job search failed.'))
    } finally {
      setJobSearchLoading(false)
    }
  }

  const handleSelectJob = (job) => {
    setSelectedJob(job)
    setMatch(null)
    setSkillGap(null)
    setRoadmap(null)
    setActiveTab('match')
  }

  const handleToggleSave = async (job) => {
    const existing = savedJobs.find((s) => s.job.id === job.id)
    try {
      if (existing) {
        await api.removeSavedJob(existing.id)
        setSavedJobs((list) => list.filter((s) => s.id !== existing.id))
      } else {
        const res = await api.saveJob(job)
        setSavedJobs((list) => [res.data, ...list.filter((s) => s.id !== res.data.id)])
      }
    } catch (err) {
      setError(friendlyError(err, 'Could not update your saved jobs.'))
    }
  }

  const handleUpdateSaved = async (id, patch) => {
    const before = savedJobs
    setSavedJobs((list) => list.map((s) => (s.id === id ? { ...s, ...patch } : s))) // optimistic
    try {
      const res = await api.updateSavedJob(id, patch)
      setSavedJobs((list) => list.map((s) => (s.id === id ? res.data : s)))
    } catch (err) {
      setSavedJobs(before)
      setError(friendlyError(err, 'Could not update that job.'))
    }
  }

  const handleRemoveSaved = async (id) => {
    try {
      await api.removeSavedJob(id)
      setSavedJobs((list) => list.filter((s) => s.id !== id))
    } catch (err) {
      setError(friendlyError(err, 'Could not remove that job.'))
    }
  }

  const restoreRun = (p) => {
    setSelectedJob(p.job || null)
    setJobs(p.job ? [p.job] : [])
    setMatch(p.match || null)
    setSkillGap(p.skill_gap || null)
    setRoadmap(p.roadmap || null)
    setInterviewQuestions(p.interview_questions || [])
    setActiveTab('match')
  }

  const saveSnapshot = (job, parts) => {
    if (!job) return
    api.saveHistory({ job, ...parts }).catch(() => {})
  }

  const runMatchAndGap = async () => {
    if (!profile || !selectedJob) {
      setError('Upload your resume on the Overview tab before running an analysis.')
      return
    }
    setError('')
    setMatchLoading(true)
    try {
      const matchRes = await api.matchScore(profile, selectedJob)
      setMatch(matchRes.data)
      const gapRes = await api.skillGap(profile, selectedJob)
      setSkillGap(gapRes.data)
      saveSnapshot(selectedJob, {
        match: matchRes.data,
        skill_gap: gapRes.data,
      })
    } catch (err) {
      setError(friendlyError(err, 'Analysis failed.'))
    } finally {
      setMatchLoading(false)
    }
  }

  const generateRoadmap = async () => {
    if (!skillGap) return
    setError('')
    setRoadmapLoading(true)
    try {
      const res = await api.learningRoadmap(skillGap.priority_order)
      setRoadmap(res.data)
      saveSnapshot(selectedJob, {
        match,
        skill_gap: skillGap,
        roadmap: res.data,
        interview_questions: interviewQuestions,
      })
    } catch (err) {
      setError(friendlyError(err, 'Roadmap generation failed.'))
    } finally {
      setRoadmapLoading(false)
    }
  }

  const generateInterview = async (role) => {
    setError('')
    setInterviewLoading(true)
    try {
      const res = await api.generateInterview(role, profile)
      setInterviewQuestions(res.data.questions)
      // Only attach questions to the saved job if they were generated for that role.
      if (selectedJob && role.trim().toLowerCase() === selectedJob.title.toLowerCase()) {
        saveSnapshot(selectedJob, {
          match,
          skill_gap: skillGap,
          roadmap,
          interview_questions: res.data.questions,
        })
      }
    } catch (err) {
      setError(friendlyError(err, 'Question generation failed.'))
    } finally {
      setInterviewLoading(false)
    }
  }

  const handleChat = async (message) => {
    const res = await api.chat(message, profile, sessionIdRef.current)
    return res.data.reply
  }

  // Which sidebar tabs are usable yet, and what to suggest after each stage.
  const ready = { profile: !!profile, job: !!selectedJob, match: !!skillGap }
  const nextStep = {
    overview: ready.profile && { done: 'Resume ready', next: 'Search jobs', to: 'jobs' },
    match: ready.match && { done: 'Analysis complete', next: 'Build my roadmap', to: 'learning' },
    learning: roadmap && { done: 'Roadmap ready', next: 'Practice interview', to: 'interview' },
  }[activeTab]

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        active={activeTab}
        onChange={changeTab}
        user={user}
        onLogout={onLogout}
        ready={ready}
      />

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-8 py-10">
          {error && (
            <div
              role="alert"
              className="mb-6 px-4 py-3 rounded-md bg-signal-red/10 border border-signal-red/20 text-signal-red text-sm"
            >
              {error}
            </div>
          )}

          {activeTab === 'overview' && (
            <Overview
              profile={profile}
              onResumeUploaded={handleResumeUpload}
              onResumeError={setError}
              onProfileChange={handleProfileChange}
              onDeleteData={handleDeleteData}
              resumeLoading={resumeLoading}
              setResumeLoading={setResumeLoading}
              match={match}
              skillGap={skillGap}
              roadmap={roadmap}
              interviewQuestions={interviewQuestions}
              onChat={handleChat}
              onNavigate={changeTab}
            />
          )}

          {activeTab === 'jobs' && (
            <JobSearch
              onSearch={handleJobSearch}
              jobs={jobs}
              toolUsed={toolUsed}
              onSelectJob={handleSelectJob}
              selectedJobId={selectedJob?.id}
              loading={jobSearchLoading}
              savedIds={savedIds}
              onToggleSave={handleToggleSave}
            />
          )}

          {activeTab === 'match' && (
            <MatchScore
              job={selectedJob}
              match={match}
              skillGap={skillGap}
              loading={matchLoading}
              onAnalyze={runMatchAndGap}
            />
          )}

          {activeTab === 'learning' && (
            <LearningRoadmap
              skillGap={skillGap}
              roadmap={roadmap}
              loading={roadmapLoading}
              onGenerate={generateRoadmap}
            />
          )}

          {activeTab === 'interview' && (
            <InterviewPrep
              questions={interviewQuestions}
              loading={interviewLoading}
              onGenerate={generateInterview}
              defaultRole={selectedJob?.title}
            />
          )}

          {activeTab === 'history' && <HistoryPanel onRestore={restoreRun} />}

          {activeTab === 'calendar' && (
            <PlacementCalendar savedIds={savedIds} onToggleSave={handleToggleSave} />
          )}

          {activeTab === 'tracker' && (
            <SavedJobs
              items={savedJobs}
              onUpdate={handleUpdateSaved}
              onRemove={handleRemoveSaved}
              onAnalyze={handleSelectJob}
              onNavigate={changeTab}
            />
          )}

          {nextStep && (
            <NextStep
              done={nextStep.done}
              next={nextStep.next}
              onClick={() => changeTab(nextStep.to)}
            />
          )}
        </div>
      </main>
    </div>
  )
}
