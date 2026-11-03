import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import StatCard from './StatCard'

const Icon = () => <svg data-testid="icon" />

describe('StatCard', () => {
  it('shows the label and value', () => {
    render(<StatCard icon={Icon} label="Skills found" value={12} onClick={undefined} />)
    expect(screen.getByText('Skills found')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByTestId('icon')).toBeInTheDocument()
  })

  it('is disabled without onClick', () => {
    render(<StatCard icon={Icon} label="Skills" value={1} onClick={undefined} />)
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('calls onClick when provided', async () => {
    const onClick = vi.fn()
    render(<StatCard icon={Icon} label="Skills" value={1} onClick={onClick} />)
    await userEvent.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalledTimes(1)
  })
})
