import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import JobSearch from './JobSearch'

const job = {
  id: 'j1',
  title: 'Backend Intern',
  company: 'Acme',
  location: 'Pune',
  description: 'Python and Docker',
  url: 'https://acme.test/job',
  source: 'tavily',
}

function setup(props = {}) {
  const handlers = { onSearch: vi.fn(), onSelectJob: vi.fn(), onToggleSave: vi.fn() }
  render(
    <JobSearch
      jobs={[]}
      toolUsed=""
      selectedJobId={undefined}
      loading={false}
      savedIds={new Set()}
      {...handlers}
      {...props}
    />,
  )
  return handlers
}

describe('JobSearch', () => {
  it('does not search for a blank query', async () => {
    const { onSearch } = setup()
    await userEvent.click(screen.getByRole('button', { name: /^search$/i }))
    expect(onSearch).not.toHaveBeenCalled()
  })

  it('searches with query, location and job type', async () => {
    const user = userEvent.setup()
    const { onSearch } = setup()
    await user.type(screen.getByPlaceholderText(/backend engineer intern/i), 'python')
    await user.type(screen.getByPlaceholderText(/location/i), 'Pune')
    await user.selectOptions(screen.getByLabelText('Job type'), 'internship')
    await user.click(screen.getByRole('button', { name: /^search$/i }))
    expect(onSearch).toHaveBeenCalledWith('python', 'Pune', 'internship')
  })

  it('shows a hint when there are no results yet', () => {
    setup()
    expect(screen.getByText(/no results yet/i)).toBeInTheDocument()
  })

  it('shows a skeleton and disables search while loading', () => {
    setup({ loading: true, jobs: [job] })
    expect(screen.getByText('Searching for roles…')).toBeInTheDocument()
    expect(screen.queryByText('Backend Intern')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^search$/i })).toBeDisabled()
  })

  it('lists jobs and the tool that found them', () => {
    setup({ jobs: [job], toolUsed: 'tavily_search' })
    expect(screen.getByText('Backend Intern')).toBeInTheDocument()
    expect(screen.getByText('tavily_search')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /view listing/i })).toHaveAttribute(
      'href',
      'https://acme.test/job',
    )
  })

  it('selects a job for analysis', async () => {
    const { onSelectJob } = setup({ jobs: [job] })
    await userEvent.click(screen.getByRole('button', { name: /analyze this job/i }))
    expect(onSelectJob).toHaveBeenCalledWith(job)
  })

  it('marks the selected job', () => {
    setup({ jobs: [job], selectedJobId: 'j1' })
    expect(screen.getByRole('button', { name: /selected for matching/i })).toBeInTheDocument()
  })

  it('toggles saving and reflects saved state', async () => {
    const { onToggleSave } = setup({ jobs: [job] })
    await userEvent.click(screen.getByRole('button', { name: /^save$/i }))
    expect(onToggleSave).toHaveBeenCalledWith(job)
  })

  it('shows jobs that are already saved', () => {
    setup({ jobs: [job], savedIds: new Set(['j1']) })
    expect(screen.getByRole('button', { name: /^saved$/i })).toBeInTheDocument()
  })
})
