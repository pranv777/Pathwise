import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../adminApi', () => ({
  adminApi: { drives: vi.fn(), saveDrive: vi.fn(), deleteDrive: vi.fn() },
  errMsg: (e) => e.message,
}))

import { adminApi } from '../adminApi'
import Drives from './Drives'

const drive = {
  id: 'drive-1',
  company: 'Acme',
  role: 'Engineer',
  type: 'full-time',
  date: '2999-01-01',
  branches: ['CSE'],
  min_cgpa: 7,
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(adminApi.drives).mockResolvedValue([drive])
  vi.mocked(adminApi.saveDrive).mockResolvedValue({ ...drive, id: 'drive-2' })
  vi.mocked(adminApi.deleteDrive).mockResolvedValue(undefined)
})

describe('Drives page', () => {
  it('lists drives with an active state for future dates', async () => {
    render(<Drives />)
    expect(await screen.findByText('Acme')).toBeInTheDocument()
    expect(screen.getByText('active')).toBeInTheDocument()
  })

  it('creates a drive from the form', async () => {
    const user = userEvent.setup()
    render(<Drives />)
    await user.click(await screen.findByRole('button', { name: /new drive/i }))
    await user.type(screen.getByLabelText('Company'), 'Globex')
    await user.type(screen.getByLabelText('Role'), 'Analyst')
    await user.type(screen.getByLabelText('Drive date'), '2999-06-01')
    await user.click(screen.getByRole('button', { name: 'Save' }))
    expect(adminApi.saveDrive).toHaveBeenCalledWith(
      expect.objectContaining({ company: 'Globex', role: 'Analyst', date: '2999-06-01' }),
    )
  })

  it('does not delete when the confirmation is declined', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const user = userEvent.setup()
    render(<Drives />)
    await user.click(await screen.findByRole('button', { name: 'Delete' }))
    expect(adminApi.deleteDrive).not.toHaveBeenCalled()
  })

  it('deletes after confirmation', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()
    render(<Drives />)
    await user.click(await screen.findByRole('button', { name: 'Delete' }))
    expect(adminApi.deleteDrive).toHaveBeenCalledWith('drive-1')
  })
})
