import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../adminApi', () => ({
  adminApi: { agents: vi.fn(), runs: vi.fn() },
  errMsg: (e) => e.message,
}))

import { adminApi } from '../adminApi'
import Agents from './Agents'

const agents = [
  { name: 'resume', runs: 4, failed: 1, success_rate: 75, avg_ms: 20, last_run: null },
  { name: 'learning', runs: 0, failed: 0, success_rate: null, avg_ms: null, last_run: null },
]
const run = {
  id: 1,
  at: null,
  name: 'resume',
  status: 'failed',
  duration_ms: 30,
  error: 'KeyError',
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(adminApi.agents).mockResolvedValue(agents)
  vi.mocked(adminApi.runs).mockResolvedValue([run])
})

describe('Agents page', () => {
  it('shows a card per agent with its stats', async () => {
    render(<Agents />)
    expect(await screen.findByText('4 runs')).toBeInTheDocument()
    expect(screen.getByText('Success 75%')).toBeInTheDocument()
    expect(screen.getByText('Avg 20 ms')).toBeInTheDocument()
    expect(screen.getByText('1 failed')).toBeInTheDocument()
    expect(screen.getByText('Success —')).toBeInTheDocument()
    expect(screen.getByText('Avg —')).toBeInTheDocument()
  })

  it('lists the execution history', async () => {
    render(<Agents />)
    expect(await screen.findByText('KeyError')).toBeInTheDocument()
    expect(screen.getByText('30 ms')).toBeInTheDocument()
    expect(adminApi.runs).toHaveBeenCalledWith({
      kind: 'agent',
      name: undefined,
      status: undefined,
    })
  })

  it('filters runs by agent and clears the filter on a second click', async () => {
    const user = userEvent.setup()
    render(<Agents />)
    await user.click(await screen.findByRole('button', { name: /resume/ }))
    await waitFor(() =>
      expect(adminApi.runs).toHaveBeenLastCalledWith(expect.objectContaining({ name: 'resume' })),
    )
    expect(screen.getByText(/Execution history · resume/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /resume/ }))
    await waitFor(() =>
      expect(adminApi.runs).toHaveBeenLastCalledWith(expect.objectContaining({ name: undefined })),
    )
  })

  it('filters runs by status', async () => {
    const user = userEvent.setup()
    render(<Agents />)
    await screen.findByText('KeyError')
    await user.selectOptions(screen.getByLabelText('Filter by status'), 'failed')
    await waitFor(() =>
      expect(adminApi.runs).toHaveBeenLastCalledWith(expect.objectContaining({ status: 'failed' })),
    )
  })

  it('refreshes both lists', async () => {
    const user = userEvent.setup()
    render(<Agents />)
    await screen.findByText('KeyError')
    await user.click(screen.getByRole('button', { name: 'Refresh' }))
    await waitFor(() => expect(adminApi.agents).toHaveBeenCalledTimes(2))
    expect(adminApi.runs).toHaveBeenCalledTimes(2)
  })

  it('explains an empty history and shows load errors', async () => {
    vi.mocked(adminApi.runs).mockResolvedValue([])
    vi.mocked(adminApi.agents).mockRejectedValue(new Error('nope'))
    render(<Agents />)
    expect(await screen.findByText(/No executions recorded yet/)).toBeInTheDocument()
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })
})
