import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../adminApi', () => ({
  adminApi: { overview: vi.fn() },
  errMsg: (e) => e.message,
}))

import { adminApi } from '../adminApi'
import Overview from './Overview'

const overview = (stats = {}) => ({
  stats: {
    students: 10,
    active_students: 4,
    resumes: 7,
    saved_jobs: 5,
    active_drives: 2,
    ai_interactions: 30,
    agent_success_rate: 95,
    agent_failures: 0,
    ...stats,
  },
  registrations: [
    { date: '2026-01-01', count: 1 },
    { date: '2026-01-02', count: 2 },
  ],
  activity: [{ date: '2026-01-01', count: 3 }],
  agent_usage: [{ name: 'resume', count: 9 }],
  placement_pipeline: [{ status: 'applied', count: 2 }],
})

beforeEach(() => vi.clearAllMocks())

describe('Overview page', () => {
  it('shows a loading state, then the KPIs and charts', async () => {
    vi.mocked(adminApi.overview).mockResolvedValue(overview())
    render(<Overview />)
    expect(screen.getByText('Loading…')).toBeInTheDocument()
    expect(await screen.findByText('10')).toBeInTheDocument()
    expect(screen.getByText('4 active in 30d')).toBeInTheDocument()
    expect(screen.getByText('95%')).toBeInTheDocument()
    expect(screen.getByText('resume')).toBeInTheDocument()
    expect(screen.getByText('applied')).toBeInTheDocument()
    expect(screen.getAllByRole('img', { name: 'Trend over time' })).toHaveLength(2)
    expect(adminApi.overview).toHaveBeenCalledWith(14)
  })

  it('shows a dash when there is no success rate yet', async () => {
    vi.mocked(adminApi.overview).mockResolvedValue(overview({ agent_success_rate: null }))
    render(<Overview />)
    expect(await screen.findByText('Agent success rate')).toBeInTheDocument()
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
  })

  it('marks low success rates and failures', async () => {
    vi.mocked(adminApi.overview).mockResolvedValue(
      overview({ agent_success_rate: 80, agent_failures: 3 }),
    )
    render(<Overview />)
    expect(await screen.findByText('80%')).toHaveClass('text-red-700')
    expect(screen.getByText('3')).toHaveClass('text-red-700')
  })

  it('shows load errors', async () => {
    vi.mocked(adminApi.overview).mockRejectedValue(new Error('down'))
    render(<Overview />)
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })
})
