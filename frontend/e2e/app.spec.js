import { expect, test } from '@playwright/test'

const USER = {
  id: 1,
  email: 'demo@example.com',
  name: 'Demo User',
  picture: null,
}
const PROFILE = {
  name: 'Demo User',
  email: 'demo@example.com',
  skills: ['Python', 'FastAPI'],
  education: [],
  projects: ['Built a chatbot'],
  experience: [],
  certifications: [],
}
const JOB = {
  id: 'local-1',
  title: 'Backend Intern',
  company: 'Kestrel Systems',
  location: 'Bengaluru, India',
  description: 'Python and Docker role',
  url: '',
  source: 'local',
}
const MATCH = {
  match_score: 82,
  matched_skills: ['Python'],
  missing_skills: ['Docker'],
  rationale: 'Strong overlap on the core stack.',
}
const GAP = {
  missing_skills: ['Docker'],
  priority_order: ['Docker'],
  explanation: 'Docker is required.',
}

async function mockApi(page, { authed = true } = {}) {
  await page.route('https://accounts.google.com/**', (route) => route.abort())
  // Predicate, not a glob: '**/api/**' would also match Vite's /src/api/client.js
  await page.route(
    (url) => url.pathname.startsWith('/api/'),
    async (route) => {
      const { pathname } = new URL(route.request().url())
      const json = (body, status = 200) => route.fulfill({ status, json: body })
      switch (pathname) {
        case '/api/auth/me':
          return authed ? json(USER) : json({ detail: 'Not authenticated.' }, 401)
        case '/api/resume/upload':
          return json({ profile: PROFILE, summary: 'Extracted 2 skills.' })
        case '/api/jobs/search':
          return json({ jobs: [JOB], tool_used: 'local_fallback' })
        case '/api/matching/score':
          return json(MATCH)
        case '/api/skills/gap':
          return json(GAP)
        case '/api/history/snapshot':
          return json({ status: 'saved' })
        case '/api/profile':
          return json({ profile: null })
        case '/api/saved-jobs':
          return json([])
        case '/api/campus/drives':
          return json([])
        default:
          return json({ detail: `unmocked ${pathname}` }, 404)
      }
    },
  )
}

test('logged-out users see the login page', async ({ page }) => {
  await mockApi(page, { authed: false })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Wayfind' })).toBeVisible()
  await expect(page.getByText(/sign in to continue/i)).toBeVisible()
})

test('upload resume, search a job, run the match analysis', async ({ page }) => {
  await mockApi(page)
  await page.goto('/')

  await page.setInputFiles('input[type=file]', {
    name: 'resume.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.4 fake'),
  })
  await expect(page.getByText('Profile saved')).toBeVisible()

  await page.getByRole('button', { name: 'Job Search' }).click()
  await page.getByPlaceholder(/backend engineer intern/i).fill('backend intern')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page.getByText('Kestrel Systems')).toBeVisible()

  await page.getByRole('button', { name: 'Analyze this job' }).click()
  await page.getByRole('button', { name: 'Run analysis' }).click()

  await expect(page.getByText('82')).toBeVisible()
  await expect(page.getByText('Missing skills')).toBeVisible()
  await expect(page.getByText('Docker', { exact: true }).first()).toBeVisible()
})
