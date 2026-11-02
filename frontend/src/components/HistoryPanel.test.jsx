import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

vi.mock('../api/client.js', () => ({ default: { history: vi.fn() } }))

import api from '../api/client.js'
import HistoryPanel from './HistoryPanel.jsx'

const mockHistory = /** @type {any} */ (api.history)

describe('HistoryPanel', () => {
  it('lists analyses and restores one', async () => {
    const payload = {
      job: { title: 'SWE Intern', company: 'Kestrel' },
      match: { match_score: 80 },
      skill_gap: { missing_skills: ['Docker'] },
    }
    mockHistory.mockResolvedValue({
      data: [
        {
          id: 1,
          kind: 'analysis',
          created_at: '2026-10-23T10:00:00+00:00',
          payload,
        },
      ],
    })
    const onRestore = vi.fn()
    render(<HistoryPanel onRestore={onRestore} />)

    expect(await screen.findByText(/SWE Intern · Kestrel/)).toBeInTheDocument()
    expect(screen.getByText(/match 80/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /restore/i }))
    expect(onRestore).toHaveBeenCalledWith(payload)
  })

  it('shows an empty state', async () => {
    mockHistory.mockResolvedValue({ data: [] })
    render(<HistoryPanel onRestore={vi.fn()} />)
    expect(await screen.findByText(/nothing yet/i)).toBeInTheDocument()
  })
})
