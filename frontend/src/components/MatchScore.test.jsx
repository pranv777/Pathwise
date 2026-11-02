import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import MatchScore from './MatchScore.jsx'

const job = { id: '1', title: 'Backend Intern', company: 'Acme' }
const match = {
  match_score: 82,
  matched_skills: ['Python'],
  missing_skills: ['Docker'],
  rationale: 'Strong overlap on the core stack.',
}

describe('MatchScore', () => {
  it('asks the user to pick a job first', () => {
    render(<MatchScore job={null} onAnalyze={vi.fn()} />)
    expect(screen.getByText(/select a job from job search first/i)).toBeInTheDocument()
  })

  it('shows the score, rationale and skill chips', () => {
    render(<MatchScore job={job} match={match} loading={false} onAnalyze={vi.fn()} />)
    expect(screen.getByText('82')).toBeInTheDocument()
    expect(screen.getByText(/strong overlap/i)).toBeInTheDocument()
    expect(screen.getByText('Python')).toBeInTheDocument()
    expect(screen.getByText('Docker')).toBeInTheDocument()
  })

  it('runs the analysis when the button is clicked', async () => {
    const onAnalyze = vi.fn()
    render(<MatchScore job={job} match={null} loading={false} onAnalyze={onAnalyze} />)
    await userEvent.click(screen.getByRole('button', { name: /run analysis/i }))
    expect(onAnalyze).toHaveBeenCalledTimes(1)
  })
})
