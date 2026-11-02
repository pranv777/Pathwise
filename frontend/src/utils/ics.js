const pad = (n) => String(n).padStart(2, '0')
const ymd = (d) => `${d.getUTCFullYear()}${pad(d.getUTCMonth() + 1)}${pad(d.getUTCDate())}`
const esc = (s = '') =>
  s.replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n')

// Downloads a one-day calendar event for a campus drive.
export function downloadDriveIcs(drive) {
  const start = new Date(`${drive.date}T00:00:00Z`)
  const end = new Date(start.getTime() + 24 * 60 * 60 * 1000)
  const stamp = new Date().toISOString().replace(/[-:]/g, '').split('.')[0]
  const lines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Wayfind//Placement Calendar//EN',
    'BEGIN:VEVENT',
    `UID:${drive.id}@wayfind`,
    `DTSTAMP:${stamp}Z`,
    `DTSTART;VALUE=DATE:${ymd(start)}`,
    `DTEND;VALUE=DATE:${ymd(end)}`,
    `SUMMARY:${esc(`${drive.company} - ${drive.role}`)}`,
    `DESCRIPTION:${esc(`${drive.description} Apply by ${drive.apply_by}.`)}`,
    `LOCATION:${esc(drive.location)}`,
    'END:VEVENT',
    'END:VCALENDAR',
  ]
  const blob = new Blob([lines.join('\r\n')], { type: 'text/calendar' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `${drive.company.replace(/\W+/g, '-')}-drive.ics`
  a.click()
  URL.revokeObjectURL(a.href)
}

// Shape a campus drive like a job listing so it can go into the tracker.
export const driveToJob = (d) => ({
  id: d.id,
  title: d.role,
  company: d.company,
  location: d.location,
  description: `${d.description}\n\nDrive date: ${d.date}. Apply by: ${d.apply_by}.`,
  url: d.url || '',
  source: 'campus',
})
