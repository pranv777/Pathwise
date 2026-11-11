import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../context/useAuth.js', () => ({ useAuth: () => ({ logout: vi.fn() }) }))
vi.mock('./ResumeUpload.jsx', () => ({ default: () => <div>resume-upload</div> }))
vi.mock('./GitHubCard.jsx', () => ({ default: () => <div>github-card</div> }))
vi.mock('./DeleteDataButton.jsx', () => ({ default: () => <div>delete-data</div> }))
vi.mock('./DeleteAccountButton.jsx', () => ({ default: () => <div>delete-account</div> }))

import Overview from './Overview'

const base = () => ({
  profile: { name: 'Asha Rao', skills: [] },
  onResumeUploaded: vi.fn(),
  onResumeError: vi.fn(),
  onProfileChange: vi.fn(),
  onDeleteData: vi.fn(),
  resumeLoading: false,
  setResumeLoading: vi.fn(),
  match: null,
  skillGap: null,
  roadmap: null,
  interviewQuestions: [],
  onChat: vi.fn().mockResolvedValue('Hello **there**'),
  onNavigate: vi.fn(),
})

beforeEach(() => vi.clearAllMocks())

describe('Overview', () => {
  it('greets the user by first name, or shows the product name', () => {
    const { unmount } = render(<Overview {...base()} />)
    expect(screen.getByRole('heading', { name: 'Welcome back, Asha' })).toBeInTheDocument()
    unmount()
    render(<Overview {...base()} profile={null} />)
    expect(screen.getByRole('heading', { name: 'Pathwise' })).toBeInTheDocument()
  })

  it('hides the stat cards until there are results', () => {
    render(<Overview {...base()} />)
    expect(screen.queryByText('Match score')).not.toBeInTheDocument()
    expect(screen.getByText('resume-upload')).toBeInTheDocument()
    expect(screen.getByText('delete-account')).toBeInTheDocument()
  })

  it.each([
    [80, 'text-signal-green'],
    [50, 'text-signal-amber'],
    [10, 'text-signal-red'],
  ])('colours a match score of %i', (score, tone) => {
    render(<Overview {...base()} match={{ match_score: score }} />)
    const card = screen.getByText('Match score').closest('button')
    expect(card?.firstElementChild?.className).toContain(tone)
  })

  it('shows each stat and navigates when clicked', async () => {
    const props = {
      ...base(),
      match: { match_score: 72 },
      skillGap: { missing_skills: ['a', 'b'] },
      roadmap: { total_estimated_weeks: 5 },
      interviewQuestions: [{}, {}, {}],
    }
    const user = userEvent.setup()
    render(<Overview {...props} />)
    expect(screen.getByText('72')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('5w')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    await user.click(screen.getByText('Roadmap'))
    expect(props.onNavigate).toHaveBeenCalledWith('learning')
    await user.click(screen.getByText('Interview Qs'))
    expect(props.onNavigate).toHaveBeenCalledWith('interview')
    await user.click(screen.getByText('Skill gaps'))
    expect(props.onNavigate).toHaveBeenCalledWith('match')
  })

  it('shows dashes for stats that are not available yet', () => {
    render(<Overview {...base()} match={{ match_score: 40 }} />)
    expect(screen.getAllByText('—')).toHaveLength(3)
  })

  it('chats with the assistant and renders markdown replies', async () => {
    const props = base()
    const user = userEvent.setup()
    render(<Overview {...props} />)
    expect(screen.getByText('Ask me anything about your job search.')).toBeInTheDocument()
    await user.type(screen.getByPlaceholderText('Ask a question…'), 'find me jobs{enter}')
    expect(await screen.findByText('there')).toBeInTheDocument()
    expect(props.onChat).toHaveBeenCalledWith('find me jobs')
    expect(screen.getByText('find me jobs')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Ask a question…')).toHaveValue('')
  })

  it('ignores blank messages', async () => {
    const props = base()
    const user = userEvent.setup()
    render(<Overview {...props} />)
    await user.type(screen.getByPlaceholderText('Ask a question…'), '   {enter}')
    expect(props.onChat).not.toHaveBeenCalled()
  })

  it('shows a friendly error when the assistant fails', async () => {
    const props = base()
    props.onChat.mockRejectedValue({ response: { status: 429 } })
    const user = userEvent.setup()
    render(<Overview {...props} />)
    await user.type(screen.getByPlaceholderText('Ask a question…'), 'hi{enter}')
    await waitFor(() => expect(screen.getByText(/Too many requests/)).toBeInTheDocument())
  })

  it('shows a thinking indicator while waiting', async () => {
    const props = base()
    /** @type {(value: string) => void} */
    let resolve = () => {}
    props.onChat.mockReturnValue(new Promise((r) => (resolve = r)))
    const user = userEvent.setup()
    render(<Overview {...props} />)
    await user.type(screen.getByPlaceholderText('Ask a question…'), 'hi{enter}')
    expect(await screen.findByText(/thinking/)).toBeInTheDocument()
    resolve('done')
    expect(await screen.findByText('done')).toBeInTheDocument()
  })
})
