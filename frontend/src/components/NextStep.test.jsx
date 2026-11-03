import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import NextStep from './NextStep'

describe('NextStep', () => {
  it('shows what is done and a button for the next step', () => {
    render(<NextStep done="Resume uploaded" next="Find jobs" onClick={() => {}} />)
    expect(screen.getByText('Resume uploaded')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /find jobs/i })).toBeInTheDocument()
  })

  it('calls onClick when the button is pressed', async () => {
    const onClick = vi.fn()
    render(<NextStep done="Done" next="Continue" onClick={onClick} />)
    await userEvent.click(screen.getByRole('button', { name: /continue/i }))
    expect(onClick).toHaveBeenCalledTimes(1)
  })
})
