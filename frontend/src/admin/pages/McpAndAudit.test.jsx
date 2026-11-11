import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../adminApi', () => ({
  adminApi: { mcp: vi.fn(), runs: vi.fn(), audit: vi.fn() },
  errMsg: (e) => e.message,
}))

import { adminApi } from '../adminApi'
import { Audit, Mcp } from './McpAndAudit'

const servers = [
  {
    id: 'job_search',
    name: 'Job search',
    health: 'degraded',
    tools: [{ name: 'search_jobs', calls_7d: 2, failed_7d: 1, avg_ms: 20 }],
  },
  {
    id: 'github',
    name: 'GitHub',
    health: 'unknown',
    tools: [{ name: 'analyze_github_profile', calls_7d: 0, failed_7d: 0, avg_ms: null }],
  },
]

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(adminApi.mcp).mockResolvedValue(servers)
  vi.mocked(adminApi.runs).mockResolvedValue([
    { id: 1, at: null, name: 'search_jobs', status: 'failed', duration_ms: 9, error: 'Timeout' },
  ])
  vi.mocked(adminApi.audit).mockResolvedValue([
    { id: 1, at: null, admin: 'a@x.com', action: 'kb.upload', target: 'g.txt', detail: '3 chunks' },
  ])
})

describe('Mcp page', () => {
  it('shows each server, its health and tool stats', async () => {
    render(<Mcp />)
    expect(await screen.findByText('Job search')).toBeInTheDocument()
    expect(screen.getByText('degraded')).toBeInTheDocument()
    expect(screen.getByText('20 ms')).toBeInTheDocument()
    expect(screen.getByText('analyze_github_profile')).toBeInTheDocument()
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
  })

  it('shows invocation history and asks only for MCP runs', async () => {
    render(<Mcp />)
    expect(await screen.findByText('Timeout')).toBeInTheDocument()
    expect(adminApi.runs).toHaveBeenCalledWith({ kind: 'mcp' })
  })

  it('refreshes both lists', async () => {
    const user = userEvent.setup()
    render(<Mcp />)
    await screen.findByText('Timeout')
    await user.click(screen.getByRole('button', { name: 'Refresh' }))
    await waitFor(() => expect(adminApi.mcp).toHaveBeenCalledTimes(2))
    expect(adminApi.runs).toHaveBeenCalledTimes(2)
  })

  it('handles empty history and errors', async () => {
    vi.mocked(adminApi.runs).mockResolvedValue([])
    vi.mocked(adminApi.mcp).mockRejectedValue(new Error('x'))
    render(<Mcp />)
    expect(await screen.findByText('No MCP calls recorded yet.')).toBeInTheDocument()
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })
})

describe('Audit page', () => {
  it('lists entries', async () => {
    render(<Audit />)
    expect(await screen.findByText('kb.upload')).toBeInTheDocument()
    expect(screen.getByText('a@x.com')).toBeInTheDocument()
    expect(adminApi.audit).toHaveBeenCalledWith({ action: undefined })
  })

  it('filters by action', async () => {
    const user = userEvent.setup()
    render(<Audit />)
    await screen.findByText('kb.upload')
    await user.selectOptions(screen.getByLabelText('Filter by action'), 'drive')
    await waitFor(() => expect(adminApi.audit).toHaveBeenLastCalledWith({ action: 'drive' }))
  })

  it('shows an empty state and errors', async () => {
    vi.mocked(adminApi.audit).mockResolvedValue([])
    const { unmount } = render(<Audit />)
    expect(await screen.findByText('No audit entries.')).toBeInTheDocument()
    unmount()
    vi.mocked(adminApi.audit).mockRejectedValue(new Error('x'))
    render(<Audit />)
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })
})
