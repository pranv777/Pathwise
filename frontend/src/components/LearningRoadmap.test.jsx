import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import LearningRoadmap from './LearningRoadmap'

const gap = { missing_skills: ['Docker'], priority_order: ['Docker'], explanation: '' }
const roadmap = {
  total_estimated_weeks: 6,
  roadmap: [{ skill: 'Docker', resources: ['Official docs', 'Book'], estimated_weeks: 3 }],
}

describe('LearningRoadmap', () => {
  it.each([[null], [{ missing_skills: [] }]])('asks for a skill-gap analysis first (%#)', (g) => {
    render(<LearningRoadmap skillGap={g} roadmap={null} loading={false} onGenerate={vi.fn()} />)
    expect(screen.getByText(/Run a skill-gap analysis/)).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('offers to generate when there is no roadmap yet', async () => {
    const onGenerate = vi.fn()
    const user = userEvent.setup()
    render(
      <LearningRoadmap skillGap={gap} roadmap={null} loading={false} onGenerate={onGenerate} />,
    )
    expect(screen.getByText('Not generated yet')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Generate roadmap/ }))
    expect(onGenerate).toHaveBeenCalled()
  })

  it('shows a loading skeleton and disables the button', () => {
    render(<LearningRoadmap skillGap={gap} roadmap={null} loading onGenerate={vi.fn()} />)
    expect(screen.getByText(/Building your roadmap/)).toBeInTheDocument()
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('lists each step with its resources and total time', () => {
    render(
      <LearningRoadmap skillGap={gap} roadmap={roadmap} loading={false} onGenerate={vi.fn()} />,
    )
    expect(screen.getByText('~6 weeks total')).toBeInTheDocument()
    expect(screen.getByText('Docker')).toBeInTheDocument()
    expect(screen.getByText('~3w')).toBeInTheDocument()
    expect(screen.getByText('· Official docs')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Regenerate/ })).toBeEnabled()
  })
})
