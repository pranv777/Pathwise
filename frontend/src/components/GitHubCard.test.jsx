import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import api from '../api/client.js'
import GitHubCard from './GitHubCard'

vi.mock('../api/client.js', () => ({ default: { analyzeGithub: vi.fn() } }))
const mockApi = /** @type {any} */ (api)

const result = {
  summary: 'Builds backend tools.',
  top_languages: ['Python', 'Go'],
  notable_repos: ['repo-a', 'repo-b'],
  public_repos: 12,
}
const profile = { name: 'Asha', skills: ['python'], projects: ['repo-a'] }

async function analyze(name = 'octocat') {
  const user = userEvent.setup()
  await user.type(screen.getByPlaceholderText('GitHub username'), `${name}{Enter}`)
  return user
}

describe('GitHubCard', () => {
  beforeEach(() => {
    mockApi.analyzeGithub.mockReset()
  })

  it('rejects an invalid username without calling the API', async () => {
    render(<GitHubCard profile={profile} onProfileChange={vi.fn()} />)
    await analyze('not a user!')
    expect(screen.getByText(/enter a valid github username/i)).toBeInTheDocument()
    expect(mockApi.analyzeGithub).not.toHaveBeenCalled()
  })

  it('shows the summary, languages and repos', async () => {
    mockApi.analyzeGithub.mockResolvedValue({ data: result })
    render(<GitHubCard profile={profile} onProfileChange={vi.fn()} />)
    await analyze()
    expect(await screen.findByText('Builds backend tools.')).toBeInTheDocument()
    expect(mockApi.analyzeGithub).toHaveBeenCalledWith('octocat')
    expect(screen.getByText('Go')).toBeInTheDocument()
    expect(screen.getByText(/Notable repos \(12 public\)/)).toBeInTheDocument()
  })

  it('adds only new languages to the skills (case-insensitive)', async () => {
    mockApi.analyzeGithub.mockResolvedValue({ data: result })
    const onProfileChange = vi.fn()
    render(<GitHubCard profile={profile} onProfileChange={onProfileChange} />)
    const user = await analyze()
    await user.click(await screen.findByRole('button', { name: /add languages/i }))
    expect(onProfileChange).toHaveBeenCalledWith({ ...profile, skills: ['python', 'Go'] })
    expect(screen.getByText('Added 1 skill(s) to your profile.')).toBeInTheDocument()
  })

  it('adds only new repos to the projects', async () => {
    mockApi.analyzeGithub.mockResolvedValue({ data: result })
    const onProfileChange = vi.fn()
    render(<GitHubCard profile={profile} onProfileChange={onProfileChange} />)
    const user = await analyze()
    await user.click(await screen.findByRole('button', { name: /add repos/i }))
    expect(onProfileChange).toHaveBeenCalledWith({ ...profile, projects: ['repo-a', 'repo-b'] })
  })

  it('says so when everything is already in the profile', async () => {
    mockApi.analyzeGithub.mockResolvedValue({ data: { ...result, top_languages: ['Python'] } })
    const onProfileChange = vi.fn()
    render(<GitHubCard profile={profile} onProfileChange={onProfileChange} />)
    const user = await analyze()
    await user.click(await screen.findByRole('button', { name: /add languages/i }))
    expect(onProfileChange).not.toHaveBeenCalled()
    expect(screen.getByText('Already in your profile.')).toBeInTheDocument()
  })

  it('asks for a resume first when there is no profile', async () => {
    mockApi.analyzeGithub.mockResolvedValue({ data: result })
    render(<GitHubCard profile={null} onProfileChange={vi.fn()} />)
    await analyze()
    expect(await screen.findByText(/upload your resume first/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /add languages/i })).not.toBeInTheDocument()
  })

  it('shows a friendly error when the analysis fails', async () => {
    mockApi.analyzeGithub.mockRejectedValue({ response: { status: 429, data: {} } })
    render(<GitHubCard profile={profile} onProfileChange={vi.fn()} />)
    await analyze()
    expect(await screen.findByText(/too many requests/i)).toBeInTheDocument()
    expect(screen.queryByText('Builds backend tools.')).not.toBeInTheDocument()
  })
})
