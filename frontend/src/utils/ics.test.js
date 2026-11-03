import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { downloadDriveIcs, driveToJob } from './ics'

const drive = {
  id: 'd1',
  company: 'Kestrel Systems',
  role: 'SDE Intern',
  location: 'Bengaluru, India',
  description: 'Build things; learn.',
  date: '2026-11-20',
  apply_by: '2026-11-15',
  url: 'https://kestrel.test/apply',
}

describe('downloadDriveIcs', () => {
  let blobs
  let clicked

  beforeEach(() => {
    blobs = []
    clicked = null
    vi.stubGlobal(
      'Blob',
      class {
        constructor(parts, opts) {
          this.text = parts.join('')
          this.type = opts?.type
          blobs.push(this)
        }
      },
    )
    URL.createObjectURL = vi.fn(() => 'blob:fake')
    URL.revokeObjectURL = vi.fn()
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () {
      clicked = { download: this.download, href: this.href }
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('downloads a one-day all-day event', () => {
    downloadDriveIcs(drive)
    const lines = blobs[0].text.split('\r\n')
    expect(blobs[0].type).toBe('text/calendar')
    expect(lines[0]).toBe('BEGIN:VCALENDAR')
    expect(lines.at(-1)).toBe('END:VCALENDAR')
    expect(lines).toContain('UID:d1@wayfind')
    expect(lines).toContain('DTSTART;VALUE=DATE:20261120')
    expect(lines).toContain('DTEND;VALUE=DATE:20261121')
    expect(lines).toContain('SUMMARY:Kestrel Systems - SDE Intern')
  })

  it('escapes commas and semicolons', () => {
    downloadDriveIcs(drive)
    const lines = blobs[0].text.split('\r\n')
    expect(lines).toContain('LOCATION:Bengaluru\\, India')
    expect(lines).toContain('DESCRIPTION:Build things\\; learn. Apply by 2026-11-15.')
  })

  it('rolls the end date into the next month', () => {
    downloadDriveIcs({ ...drive, date: '2026-11-30' })
    expect(blobs[0].text).toContain('DTEND;VALUE=DATE:20261201')
  })

  it('names the file after the company and cleans up the URL', () => {
    downloadDriveIcs(drive)
    expect(clicked.download).toBe('Kestrel-Systems-drive.ics')
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:fake')
  })
})

describe('driveToJob', () => {
  it('shapes a drive like a job listing', () => {
    expect(driveToJob(drive)).toEqual({
      id: 'd1',
      title: 'SDE Intern',
      company: 'Kestrel Systems',
      location: 'Bengaluru, India',
      description: 'Build things; learn.\n\nDrive date: 2026-11-20. Apply by: 2026-11-15.',
      url: 'https://kestrel.test/apply',
      source: 'campus',
    })
  })

  it('defaults a missing url to an empty string', () => {
    expect(driveToJob({ ...drive, url: undefined }).url).toBe('')
  })
})
