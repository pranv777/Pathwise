import { expect, test } from '@playwright/test'

const USER = { id: 1, email: 'demo@example.com', name: 'Demo User' }
const OTP = '123456'
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

// `authed` is the starting session; sign-in / verify-otp flip it to true.
async function mockApi(page, { authed = true } = {}) {
  const state = { authed }
  // Predicate, not a glob: '**/api/**' would also match Vite's /src/api/client.js
  await page.route(
    (url) => url.pathname.startsWith('/api/'),
    async (route) => {
      const request = route.request()
      const { pathname } = new URL(request.url())
      const json = (body, status = 200) => route.fulfill({ status, json: body })
      switch (pathname) {
        case '/api/auth/me':
          return state.authed ? json(USER) : json({ detail: 'Not authenticated.' }, 401)
        case '/api/auth/login': {
          const { password } = request.postDataJSON()
          if (password !== 'correct-password') {
            return json({ detail: 'Incorrect email or password.' }, 401)
          }
          state.authed = true
          return json({ user: USER })
        }
        case '/api/auth/register':
          return json({ status: 'otp_sent', email: request.postDataJSON().email })
        case '/api/auth/resend-otp':
          return json({ status: 'otp_sent' })
        case '/api/auth/verify-otp': {
          if (request.postDataJSON().otp !== OTP) {
            return json({ detail: 'Incorrect code. Please try again.' }, 400)
          }
          state.authed = true
          return json({ user: USER })
        }
        case '/api/auth/logout':
          state.authed = false
          return json({ status: 'logged out' })
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
  return state
}

test.describe('authentication', () => {
  test('logged-out users see the sign-in form', async ({ page }) => {
    await mockApi(page, { authed: false })
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Wayfind' })).toBeVisible()
    await expect(page.getByText(/sign in to continue/i)).toBeVisible()
    await expect(page.getByLabel('Email')).toBeVisible()
    await expect(page.getByLabel('Password', { exact: true })).toBeVisible()
  })

  test('signs in with email and password', async ({ page }) => {
    await mockApi(page, { authed: false })
    await page.goto('/')

    await page.getByLabel('Email').fill('demo@example.com')
    await page.getByLabel('Password', { exact: true }).fill('correct-password')
    await page.getByRole('button', { name: 'Sign in', exact: true }).click()

    await expect(page.getByRole('heading', { name: 'Placement & Career Assistant' })).toBeVisible()
    await expect(page.getByText('Demo User')).toBeVisible()
  })

  test('shows an error for a wrong password', async ({ page }) => {
    await mockApi(page, { authed: false })
    await page.goto('/')

    await page.getByLabel('Email').fill('demo@example.com')
    await page.getByLabel('Password', { exact: true }).fill('wrong-password')
    await page.getByRole('button', { name: 'Sign in', exact: true }).click()

    await expect(page.getByRole('alert')).toHaveText('Incorrect email or password.')
    await expect(page.getByText(/sign in to continue/i)).toBeVisible()
  })

  test('creates an account only after the emailed code is verified', async ({ page }) => {
    await mockApi(page, { authed: false })
    await page.goto('/')

    await page.getByRole('button', { name: 'Create one' }).click()
    await page.getByLabel('Name').fill('Demo User')
    await page.getByLabel('Email').fill('demo@example.com')
    await page.getByLabel('Password (8+ characters)').fill('correct-password')
    await page.getByLabel('Confirm password').fill('correct-password')
    await page.getByRole('button', { name: 'Create account' }).click()

    // Still logged out: the OTP step comes first.
    await expect(page.getByText('Verify your email.')).toBeVisible()
    await expect(page.getByText('demo@example.com').first()).toBeVisible()

    await page.getByLabel('Verification code').fill('000000')
    await page.getByRole('button', { name: 'Verify and create account' }).click()
    await expect(page.getByRole('alert')).toHaveText('Incorrect code. Please try again.')

    await page.getByLabel('Verification code').fill(OTP)
    await page.getByRole('button', { name: 'Verify and create account' }).click()
    await expect(page.getByRole('heading', { name: 'Placement & Career Assistant' })).toBeVisible()
  })

  test('validates the sign-up form before contacting the server', async ({ page }) => {
    await mockApi(page, { authed: false })
    await page.goto('/')

    await page.getByRole('button', { name: 'Create one' }).click()
    await page.getByLabel('Name').fill('Demo User')
    await page.getByLabel('Email').fill('demo@example.com')
    await page.getByLabel('Password (8+ characters)').fill('correct-password')
    await page.getByLabel('Confirm password').fill('different-password')
    await page.getByRole('button', { name: 'Create account' }).click()

    await expect(page.getByRole('alert')).toHaveText('Passwords do not match.')
    await expect(page.getByText('Verify your email.')).toHaveCount(0)
  })

  test('logs out', async ({ page }) => {
    await mockApi(page)
    await page.goto('/')
    await page.getByTitle('Log out').click()
    await expect(page.getByText(/sign in to continue/i)).toBeVisible()
  })
})

test.describe('dashboard', () => {
  test('workflow tabs stay locked until a resume is uploaded', async ({ page }) => {
    await mockApi(page)
    await page.goto('/')
    await expect(page.getByRole('button', { name: 'Job Search' })).toBeDisabled()
    await expect(page.getByRole('button', { name: 'Interview Prep' })).toBeDisabled()
    await expect(page.getByRole('button', { name: 'Match & Skill Gap' })).toBeDisabled()
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
})
