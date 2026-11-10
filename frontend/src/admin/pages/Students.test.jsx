import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../adminApi', () => ({
  adminApi: {
    students: vi.fn(),
    student: vi.fn(),
    setStudentStatus: vi.fn(),
    deleteStudent: vi.fn(),
    studentsCsvUrl: () => '/api/admin/students/export.csv?',
  },
  errMsg: (e) => e.message,
}))

import { adminApi } from '../adminApi'
import Students from './Students'

const row = {
  id: 1,
  email: 'asha@example.com',
  name: 'Asha',
  status: 'active',
  created_at: null,
  last_login_at: null,
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(adminApi.students).mockResolvedValue({ total: 1, page: 1, items: [row] })
  vi.mocked(adminApi.student).mockResolvedValue({
    ...row,
    skills: ['Python'],
    activity: [],
    saved_jobs: [],
  })
  vi.mocked(adminApi.setStudentStatus).mockResolvedValue({ ...row, status: 'suspended' })
})

describe('Students page', () => {
  it('lists students', async () => {
    render(<Students />)
    expect(await screen.findByText('asha@example.com')).toBeInTheDocument()
  })

  it('searches as the admin types', async () => {
    const user = userEvent.setup()
    render(<Students />)
    await screen.findByText('asha@example.com')
    await user.type(screen.getByLabelText('Search students'), 'ash')
    await waitFor(() =>
      expect(adminApi.students).toHaveBeenLastCalledWith(expect.objectContaining({ q: 'ash' })),
    )
  })

  it('filters by status', async () => {
    const user = userEvent.setup()
    render(<Students />)
    await screen.findByText('asha@example.com')
    await user.selectOptions(screen.getByLabelText('Filter by status'), 'suspended')
    await waitFor(() =>
      expect(adminApi.students).toHaveBeenLastCalledWith(
        expect.objectContaining({ status: 'suspended' }),
      ),
    )
  })

  it('opens the drawer and suspends a student', async () => {
    const user = userEvent.setup()
    render(<Students />)
    await user.click(await screen.findByText('asha@example.com'))
    expect(await screen.findByRole('dialog', { name: /student details/i })).toBeInTheDocument()
    expect(await screen.findByText('Python')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Suspend' }))
    expect(adminApi.setStudentStatus).toHaveBeenCalledWith(1, 'suspended')
  })

  it('does not delete when the confirmation is declined', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const user = userEvent.setup()
    render(<Students />)
    await user.click(await screen.findByText('asha@example.com'))
    await user.click(await screen.findByRole('button', { name: /delete account/i }))
    expect(adminApi.deleteStudent).not.toHaveBeenCalled()
  })

  it('shows an error when the list fails to load', async () => {
    vi.mocked(adminApi.students).mockRejectedValue(new Error('boom'))
    render(<Students />)
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })
})
