import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { useAuth } from './context/useAuth.js'

vi.stubGlobal('crypto', { randomUUID: () => 'test-session' })

const apiMock = vi.hoisted(() => ({
  getProfile: vi.fn(),
  savedJobs: vi.fn(),
  saveProfile: vi.fn(),
  deleteMyData: vi.fn(),
  searchJobs: vi.fn(),
  saveJob: vi.fn(),
  removeSavedJob: vi.fn(),
  updateSavedJob: vi.fn(),
}))

vi.mock('./api/client.js', () => ({ default: apiMock }))
vi.mock('./context/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('./components/LoginPage.jsx', () => ({ default: () => <div>login page</div> }))
vi.mock('./components/ResumeUpload.jsx', () => ({ default: () => <div>resume upload</div> }))
vi.mock('./components/GitHubCard.jsx', () => ({ default: () => <div>github card</div> }))

const mockUseAuth = /** @type {any} */ (useAuth)
const user = { id: 1, name: 'Asha Rao', email: 'asha@example.com' }
const profile = { name: 'Asha Rao', skills: ['Python'], projects: [] }
const job = {
  id: 'j1',
  title: 'Backend Intern',
  company: 'Acme',
  location: 'Pune',
  description: 'Python',
  url: '',
  source: 'local',
}

const signedIn = (logout = vi.fn()) => mockUseAuth.mockReturnValue({ user, loading: false, logout })

describe('App', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve({})),
    )
    sessionStorage.clear()
    Object.values(apiMock).forEach((fn) => fn.mockReset())
    apiMock.getProfile.mockResolvedValue({ data: { profile: null } })
    apiMock.savedJobs.mockResolvedValue({ data: [] })
    apiMock.searchJobs.mockResolvedValue({ data: { jobs: [job], tool_used: 'local_fallback' } })
  })

  it('shows a loading state while the session is checked', () => {
    mockUseAuth.mockReturnValue({ user: null, loading: true, logout: vi.fn() })
    render(<App />)
    expect(screen.getByText('Loading…')).toBeInTheDocument()
  })

  it('shows the login page when signed out', () => {
    mockUseAuth.mockReturnValue({ user: null, loading: false, logout: vi.fn() })
    render(<App />)
    expect(screen.getByText('login page')).toBeInTheDocument()
  })

  it('shows the dashboard when signed in and logs out', async () => {
    const logout = vi.fn()
    signedIn(logout)
    render(<App />)
    expect(
      screen.getByRole('heading', { name: 'Placement & Career Assistant' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Asha Rao')).toBeInTheDocument()
    await userEvent.click(screen.getByTitle('Log out'))
    expect(logout).toHaveBeenCalledTimes(1)
  })

  it('locks the workflow tabs until a resume exists', () => {
    signedIn()
    render(<App />)
    expect(screen.getByRole('button', { name: 'Job Search' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Match & Skill Gap' })).toBeDisabled()
  })

  it('restores a saved profile and unlocks job search', async () => {
    apiMock.getProfile.mockResolvedValue({ data: { profile } })
    signedIn()
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Welcome back, Asha' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Job Search' })).toBeEnabled()
    expect(screen.getByText('Resume ready')).toBeInTheDocument() // guided next step
  })

  it('searches for jobs and opens the match tab for the chosen one', async () => {
    const u = userEvent.setup()
    apiMock.getProfile.mockResolvedValue({ data: { profile } })
    signedIn()
    render(<App />)
    await screen.findByRole('heading', { name: 'Welcome back, Asha' })

    await u.click(screen.getByRole('button', { name: 'Job Search' }))
    await u.type(screen.getByPlaceholderText(/backend engineer intern/i), 'python')
    await u.click(screen.getByRole('button', { name: /^search$/i }))
    expect(apiMock.searchJobs).toHaveBeenCalledWith('python', '', 5, 'any')

    await u.click(await screen.findByRole('button', { name: /analyze this job/i }))
    expect(screen.queryByText(/select a job from job search first/i)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Match & Skill Gap' })).toBeEnabled()
  })

  it('saves a job to the tracker from search results', async () => {
    const u = userEvent.setup()
    apiMock.getProfile.mockResolvedValue({ data: { profile } })
    apiMock.saveJob.mockResolvedValue({ data: { id: 5, status: 'saved', notes: '', job } })
    signedIn()
    render(<App />)
    await screen.findByRole('heading', { name: 'Welcome back, Asha' })

    await u.click(screen.getByRole('button', { name: 'Job Search' }))
    await u.type(screen.getByPlaceholderText(/backend engineer intern/i), 'python{Enter}')
    await u.click(await screen.findByRole('button', { name: /^save$/i }))
    expect(apiMock.saveJob).toHaveBeenCalledWith(job)
    expect(await screen.findByRole('button', { name: /^saved$/i })).toBeInTheDocument()

    await u.click(screen.getByRole('button', { name: 'Application Tracker' }))
    expect(screen.getByText('Backend Intern')).toBeInTheDocument()
  })

  it('shows a friendly error when job search fails', async () => {
    const u = userEvent.setup()
    apiMock.getProfile.mockResolvedValue({ data: { profile } })
    apiMock.searchJobs.mockRejectedValue({ response: { status: 429, data: {} } })
    signedIn()
    render(<App />)
    await screen.findByRole('heading', { name: 'Welcome back, Asha' })

    await u.click(screen.getByRole('button', { name: 'Job Search' }))
    await u.type(screen.getByPlaceholderText(/backend engineer intern/i), 'python{Enter}')
    expect(await screen.findByRole('alert')).toHaveTextContent(/too many requests/i)
  })

  it('resets everything after "Delete my data"', async () => {
    const u = userEvent.setup()
    apiMock.getProfile.mockResolvedValue({ data: { profile } })
    apiMock.deleteMyData.mockResolvedValue({})
    signedIn()
    render(<App />)
    await screen.findByRole('heading', { name: 'Welcome back, Asha' })

    await u.click(screen.getByRole('button', { name: /delete my data/i }))
    await u.click(screen.getByRole('button', { name: /yes, delete everything/i }))

    expect(apiMock.deleteMyData).toHaveBeenCalledTimes(1)
    expect(
      await screen.findByRole('heading', { name: 'Placement & Career Assistant' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Job Search' })).toBeDisabled()
  })
})
