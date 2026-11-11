import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/client.js', () => ({ default: { deleteAccount: vi.fn() } }))

import api from '../api/client.js'
import DeleteAccountButton from './DeleteAccountButton'

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.deleteAccount).mockResolvedValue(/** @type {any} */ ({}))
})

describe('DeleteAccountButton', () => {
  it('only asks for a password after the first click, and can be cancelled', async () => {
    const user = userEvent.setup()
    render(<DeleteAccountButton onDeleted={vi.fn()} />)
    expect(screen.queryByPlaceholderText('Password')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Delete my account/ }))
    expect(screen.getByPlaceholderText('Password')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByPlaceholderText('Password')).not.toBeInTheDocument()
  })

  it('keeps the confirm button disabled until a password is typed', async () => {
    const user = userEvent.setup()
    render(<DeleteAccountButton onDeleted={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: /Delete my account/ }))
    const confirm = screen.getAllByRole('button', { name: /Delete my account/ })[0]
    expect(confirm).toBeDisabled()
    await user.type(screen.getByPlaceholderText('Password'), 'pw')
    expect(confirm).toBeEnabled()
  })

  it('deletes the account with the password and calls onDeleted', async () => {
    const onDeleted = vi.fn().mockResolvedValue(undefined)
    const user = userEvent.setup()
    render(<DeleteAccountButton onDeleted={onDeleted} />)
    await user.click(screen.getByRole('button', { name: /Delete my account/ }))
    await user.type(screen.getByPlaceholderText('Password'), 'secret')
    await user.click(screen.getAllByRole('button', { name: /Delete my account/ })[0])
    await waitFor(() => expect(api.deleteAccount).toHaveBeenCalledWith('secret'))
    await waitFor(() => expect(onDeleted).toHaveBeenCalled())
  })

  it('shows the server message and stays open when the password is wrong', async () => {
    vi.mocked(api.deleteAccount).mockRejectedValue({
      response: { status: 401, data: { detail: 'Incorrect password.' } },
    })
    const onDeleted = vi.fn()
    const user = userEvent.setup()
    render(<DeleteAccountButton onDeleted={onDeleted} />)
    await user.click(screen.getByRole('button', { name: /Delete my account/ }))
    await user.type(screen.getByPlaceholderText('Password'), 'nope')
    await user.click(screen.getAllByRole('button', { name: /Delete my account/ })[0])
    expect(await screen.findByText('Incorrect password.')).toBeInTheDocument()
    expect(onDeleted).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeEnabled()
  })

  it('uses a generic message for unexpected errors', async () => {
    vi.mocked(api.deleteAccount).mockRejectedValue(new Error('x'))
    const user = userEvent.setup()
    render(<DeleteAccountButton onDeleted={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: /Delete my account/ }))
    await user.type(screen.getByPlaceholderText('Password'), 'pw')
    await user.click(screen.getAllByRole('button', { name: /Delete my account/ })[0])
    expect(await screen.findByText('Could not delete your account.')).toBeInTheDocument()
  })
})
