import { useState } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import SkillsEditor from './SkillsEditor'

function Harness({ initial = ['Python'] }) {
  const [skills, setSkills] = useState(initial)
  return <SkillsEditor skills={skills} onChange={setSkills} />
}

const input = () => screen.getByPlaceholderText(/add skills/i)
const addButton = () => screen.getByRole('button', { name: /add/i })

describe('SkillsEditor', () => {
  it('lists the skills with a count', () => {
    render(<Harness initial={['Python', 'SQL']} />)
    expect(screen.getByText('Python')).toBeInTheDocument()
    expect(screen.getByText('SQL')).toBeInTheDocument()
    expect(screen.getByText(/Skills \(2\)/)).toBeInTheDocument()
  })

  it('adds a skill with the Add button and clears the input', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    await user.type(input(), 'Docker')
    await user.click(addButton())
    expect(screen.getByText('Docker')).toBeInTheDocument()
    expect(input()).toHaveValue('')
  })

  it('adds a skill with Enter', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    await user.type(input(), 'Docker{Enter}')
    expect(screen.getByText('Docker')).toBeInTheDocument()
  })

  it('adds several comma-separated skills at once', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    await user.type(input(), 'Docker, FastAPI ,, Redis')
    await user.click(addButton())
    for (const name of ['Docker', 'FastAPI', 'Redis']) {
      expect(screen.getByText(name)).toBeInTheDocument()
    }
    expect(screen.getByText(/Skills \(4\)/)).toBeInTheDocument()
  })

  it('ignores duplicates regardless of case', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    await user.type(input(), 'python, PYTHON')
    await user.click(addButton())
    expect(screen.getByText(/Skills \(1\)/)).toBeInTheDocument()
  })

  it('does nothing for blank input', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    await user.type(input(), '  ,  ')
    await user.click(addButton())
    expect(screen.getByText(/Skills \(1\)/)).toBeInTheDocument()
  })

  it('truncates very long skill names to 60 characters', async () => {
    const user = userEvent.setup()
    render(<Harness initial={[]} />)
    await user.type(input(), 'x'.repeat(100))
    await user.click(addButton())
    expect(screen.getByText('x'.repeat(60))).toBeInTheDocument()
  })

  it('stops adding at 100 skills', async () => {
    const user = userEvent.setup()
    const many = Array.from({ length: 100 }, (_, i) => `skill${i}`)
    render(<Harness initial={many} />)
    await user.type(input(), 'extra')
    await user.click(addButton())
    expect(screen.queryByText('extra')).not.toBeInTheDocument()
    expect(screen.getByText(/Skills \(100\)/)).toBeInTheDocument()
  })

  it('removes a skill with its × button', async () => {
    const user = userEvent.setup()
    render(<Harness initial={['Python', 'SQL']} />)
    await user.click(screen.getByRole('button', { name: 'Remove Python' }))
    expect(screen.queryByText('Python')).not.toBeInTheDocument()
    expect(screen.getByText('SQL')).toBeInTheDocument()
  })
})
