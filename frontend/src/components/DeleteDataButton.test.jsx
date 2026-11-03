import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import DeleteDataButton from './DeleteDataButton'

const open = async (user) => user.click(screen.getByRole('button', { name: /delete my data/i }))
const confirm = () => screen.getByRole('button', { name: /yes, delete everything/i })

describe('DeleteDataButton', () => {
  it('does not delete until confirmed', async () => {
    const onDelete = vi.fn()
    const user = userEvent.setup()
    render(<DeleteDataButton onDelete={onDelete} />)
    await open(user)
    expect(screen.getByText(/permanently deletes/i)).toBeInTheDocument()
    expect(onDelete).not.toHaveBeenCalled()
  })

  it('cancel returns to the initial button', async () => {
    const user = userEvent.setup()
    render(<DeleteDataButton onDelete={vi.fn()} />)
    await open(user)
    await user.click(screen.getByRole('button', { name: /cancel/i }))
    expect(screen.getByRole('button', { name: /delete my data/i })).toBeInTheDocument()
  })

  it('calls onDelete once confirmed and closes the dialog', async () => {
    const onDelete = vi.fn().mockResolvedValue(undefined)
    const user = userEvent.setup()
    render(<DeleteDataButton onDelete={onDelete} />)
    await open(user)
    await user.click(confirm())
    expect(onDelete).toHaveBeenCalledTimes(1)
    expect(await screen.findByRole('button', { name: /delete my data/i })).toBeInTheDocument()
  })

  it('disables the buttons while deleting', async () => {
    /** @type {(value?: any) => void} */
    let finish = () => {}
    const onDelete = vi.fn(() => new Promise((resolve) => (finish = resolve)))
    const user = userEvent.setup()
    render(<DeleteDataButton onDelete={onDelete} />)
    await open(user)
    await user.click(confirm())
    expect(confirm()).toBeDisabled()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeDisabled()
    finish()
    expect(await screen.findByRole('button', { name: /delete my data/i })).toBeInTheDocument()
  })

  it('shows a friendly error and stays open when deletion fails', async () => {
    const onDelete = vi.fn().mockRejectedValue({ response: { status: 429, data: {} } })
    const user = userEvent.setup()
    render(<DeleteDataButton onDelete={onDelete} />)
    await open(user)
    await user.click(confirm())
    expect(await screen.findByText(/too many requests/i)).toBeInTheDocument()
    expect(confirm()).not.toBeDisabled()
  })
})
