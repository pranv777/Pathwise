import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import Sidebar from './Sidebar'

const user = { name: 'Asha Rao', email: 'asha@example.com' }

function setup(props = {}) {
  const onChange = vi.fn()
  const onLogout = vi.fn()
  render(
    <Sidebar active="overview" onChange={onChange} user={user} onLogout={onLogout} {...props} />,
  )
  return { onChange, onLogout }
}

const tab = (name) => screen.getByRole('button', { name })

describe('Sidebar', () => {
  it('always enables the sections that need nothing', async () => {
    const { onChange } = setup()
    for (const [label, id] of [
      ['Overview', 'overview'],
      ['Placement Calendar', 'calendar'],
      ['Application Tracker', 'tracker'],
      ['History', 'history'],
    ]) {
      await userEvent.click(tab(label))
      expect(onChange).toHaveBeenLastCalledWith(id)
    }
  })

  it('locks tabs until their prerequisite is ready, with a hint', () => {
    setup()
    expect(tab('Job Search')).toBeDisabled()
    expect(tab('Job Search')).toHaveAttribute('title', 'Upload your resume first')
    expect(tab('Interview Prep')).toBeDisabled()
    expect(tab('Match & Skill Gap')).toBeDisabled()
    expect(tab('Match & Skill Gap')).toHaveAttribute('title', 'Select a job first')
    expect(tab('Learning Roadmap')).toBeDisabled()
    expect(tab('Learning Roadmap')).toHaveAttribute('title', 'Run a match analysis first')
  })

  it('does not navigate when a locked tab is clicked', async () => {
    const { onChange } = setup()
    await userEvent.click(tab('Job Search'))
    expect(onChange).not.toHaveBeenCalled()
  })

  it('unlocks tabs as the workflow progresses', async () => {
    const { onChange } = setup({ ready: { profile: true, job: true, match: true } })
    for (const label of ['Job Search', 'Interview Prep', 'Match & Skill Gap', 'Learning Roadmap']) {
      expect(tab(label)).toBeEnabled()
    }
    await userEvent.click(tab('Learning Roadmap'))
    expect(onChange).toHaveBeenCalledWith('learning')
  })

  it('only unlocks what is ready', () => {
    setup({ ready: { profile: true } })
    expect(tab('Job Search')).toBeEnabled()
    expect(tab('Match & Skill Gap')).toBeDisabled()
  })

  it('shows the user, an initial, or the picture', () => {
    setup()
    expect(screen.getByText('Asha Rao')).toBeInTheDocument()
    expect(screen.getByText('A')).toBeInTheDocument()
  })

  it('shows the profile picture when there is one', () => {
    setup({ user: { ...user, picture: 'https://img.test/a.png' } })
    expect(screen.getByRole('img', { name: 'Asha Rao' })).toHaveAttribute(
      'src',
      'https://img.test/a.png',
    )
  })

  it('logs out', async () => {
    const { onLogout } = setup()
    await userEvent.click(screen.getByTitle('Log out'))
    expect(onLogout).toHaveBeenCalledTimes(1)
  })
})
