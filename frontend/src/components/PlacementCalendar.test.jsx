import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import api from '../api/client.js'
import { downloadDriveIcs } from '../utils/ics.js'
import PlacementCalendar from './PlacementCalendar'

vi.mock('../api/client.js', () => ({ default: { campusDrives: vi.fn() } }))
vi.mock('../utils/ics.js', () => ({
  downloadDriveIcs: vi.fn(),
  driveToJob: (d) => ({ id: d.id, title: d.role }),
}))
const mockApi = /** @type {any} */ (api)

const drive = {
  id: 'd1',
  company: 'Kestrel Systems',
  role: 'SDE Intern',
  type: 'internship',
  location: 'Bengaluru',
  pay: '₹40k/month',
  min_cgpa: 7,
  branches: ['CSE', 'IT'],
  description: 'Build things.',
  date: '2026-11-20',
  apply_by: '2026-11-15',
  days_left: 5,
  url: 'https://kestrel.test',
  eligible: true,
  reasons: [],
}
const ineligible = {
  ...drive,
  id: 'd2',
  company: 'Globex',
  role: 'Analyst',
  eligible: false,
  reasons: ['Needs CGPA 8.5+'],
  url: '',
  days_left: 0,
}

const renderCal = (props = {}) =>
  render(<PlacementCalendar savedIds={new Set()} onToggleSave={vi.fn()} {...props} />)

describe('PlacementCalendar', () => {
  beforeEach(() => {
    localStorage.clear()
    mockApi.campusDrives.mockReset()
    mockApi.campusDrives.mockResolvedValue({ data: [drive, ineligible] })
    vi.mocked(downloadDriveIcs).mockClear()
  })

  it('loads upcoming drives with the default filters', async () => {
    renderCal()
    expect(screen.getByText('Loading drives…')).toBeInTheDocument()
    expect(await screen.findByText('SDE Intern')).toBeInTheDocument()
    expect(mockApi.campusDrives).toHaveBeenCalledWith({ job_type: 'any', include_past: false })
    expect(screen.getByText('Apply by 2026-11-15 · 5d to drive')).toBeInTheDocument()
  })

  it('shows "today" for a drive happening today', async () => {
    renderCal()
    expect(await screen.findByText(/· today/)).toBeInTheDocument()
  })

  it('shows an empty message', async () => {
    mockApi.campusDrives.mockResolvedValue({ data: [] })
    renderCal()
    expect(await screen.findByText(/no drives match these filters/i)).toBeInTheDocument()
  })

  it('shows a friendly error when loading fails', async () => {
    mockApi.campusDrives.mockRejectedValue({ response: { status: 500, data: {} } })
    renderCal()
    expect(await screen.findByText(/busy or had a problem/i)).toBeInTheDocument()
    expect(screen.queryByText(/no drives match/i)).not.toBeInTheDocument()
  })

  it('sends filters when applied and remembers them', async () => {
    const user = userEvent.setup()
    renderCal()
    await screen.findByText('SDE Intern')

    await user.selectOptions(screen.getByLabelText(/^Type/), 'internship')
    await user.selectOptions(screen.getByLabelText(/^Branch/), 'CSE')
    await user.type(screen.getByLabelText(/my cgpa/i), '7.8')
    await user.type(screen.getByLabelText(/^Location/), ' Pune ')
    await user.click(screen.getByLabelText(/show past drives/i))
    await user.click(screen.getByRole('button', { name: /apply filters/i }))

    expect(mockApi.campusDrives).toHaveBeenLastCalledWith({
      job_type: 'internship',
      include_past: true,
      branch: 'CSE',
      cgpa: '7.8',
      location: 'Pune',
    })
    const saved = JSON.parse(localStorage.getItem('wayfind:campus-prefs'))
    expect(saved).toMatchObject({ jobType: 'internship', branch: 'CSE', cgpa: '7.8' })
  })

  it('restores saved filters on load', async () => {
    localStorage.setItem(
      'wayfind:campus-prefs',
      JSON.stringify({ jobType: 'full-time', branch: 'IT', cgpa: '8' }),
    )
    renderCal()
    await screen.findByText('SDE Intern')
    expect(mockApi.campusDrives).toHaveBeenCalledWith({
      job_type: 'full-time',
      include_past: false,
      branch: 'IT',
      cgpa: '8',
    })
  })

  it('survives corrupt saved filters', async () => {
    localStorage.setItem('wayfind:campus-prefs', '{not json')
    renderCal()
    expect(await screen.findByText('SDE Intern')).toBeInTheDocument()
  })

  it('prompts for branch and CGPA before checking eligibility', async () => {
    renderCal()
    await screen.findByText('SDE Intern')
    expect(screen.getAllByText(/set branch & cgpa to check eligibility/i)).toHaveLength(2)
  })

  it('shows eligibility and the reasons when a branch is set', async () => {
    localStorage.setItem('wayfind:campus-prefs', JSON.stringify({ branch: 'CSE' }))
    renderCal()
    expect(await screen.findByText("You're eligible")).toBeInTheDocument()
    expect(screen.getByText('Needs CGPA 8.5+')).toBeInTheDocument()
  })

  it('can hide drives the student is not eligible for', async () => {
    localStorage.setItem('wayfind:campus-prefs', JSON.stringify({ branch: 'CSE' }))
    renderCal()
    await screen.findByText('Analyst')
    await userEvent.click(screen.getByLabelText(/hide drives i'm not eligible for/i))
    expect(screen.queryByText('Analyst')).not.toBeInTheDocument()
    expect(screen.getByText('SDE Intern')).toBeInTheDocument()
  })

  it('adds a drive to the tracker', async () => {
    const onToggleSave = vi.fn()
    renderCal({ onToggleSave })
    await screen.findByText('SDE Intern')
    await userEvent.click(screen.getAllByRole('button', { name: /add to tracker/i })[0])
    expect(onToggleSave).toHaveBeenCalledWith({ id: 'd1', title: 'SDE Intern' })
  })

  it('shows drives that are already in the tracker', async () => {
    renderCal({ savedIds: new Set(['d1']) })
    expect(await screen.findByText('In tracker')).toBeInTheDocument()
  })

  it('exports a drive to the calendar', async () => {
    renderCal()
    await screen.findByText('SDE Intern')
    await userEvent.click(screen.getAllByRole('button', { name: /add to calendar/i })[0])
    expect(downloadDriveIcs).toHaveBeenCalledWith(drive)
  })
})
