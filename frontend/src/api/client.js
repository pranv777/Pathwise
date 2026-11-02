import axios from 'axios'

const SLOW_MS = 4000

const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
  timeout: 90000,
})

// Tell the UI when any request has been pending for a while (cold start banner).
let slowCount = 0
const notifySlow = () =>
  window.dispatchEvent(new CustomEvent('wayfind:slow', { detail: slowCount > 0 }))

const pending = new WeakMap() // request config -> { timer, slow }

const settle = (/** @type {object} */ config) => {
  const entry = pending.get(config)
  if (!entry) return
  clearTimeout(entry.timer)
  if (entry.slow) {
    slowCount -= 1
    notifySlow()
  }
  pending.delete(config)
}

client.interceptors.request.use((config) => {
  const entry = { slow: false, timer: null }
  entry.timer = setTimeout(() => {
    entry.slow = true
    slowCount += 1
    notifySlow()
  }, SLOW_MS)
  pending.set(config, entry)
  return config
})

client.interceptors.response.use(
  (res) => {
    settle(res.config)
    return res
  },
  (err) => {
    settle(err.config)
    if (err.response?.status === 401) window.location.reload()
    return Promise.reject(err)
  },
)

export const api = {
  history: () => client.get('/history'),
  saveHistory: (/** @type {any} */ snapshot) => client.post('/history/snapshot', snapshot),

  getProfile: () => client.get('/profile'),
  saveProfile: (/** @type {any} */ profile) => client.put('/profile', profile),
  deleteMyData: () => client.delete('/me/data'),

  uploadResume: (/** @type {string | Blob} */ file) => {
    const form = new FormData()
    form.append('file', file)
    return client.post('/resume/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  searchJobs: (
    /** @type {any} */ query,
    /** @type {any} */ location,
    limit = 5,
    job_type = 'any',
  ) => client.post('/jobs/search', { query, location, limit, job_type }),

  savedJobs: () => client.get('/saved-jobs'),

  saveJob: (/** @type {any} */ job, status = 'saved') =>
    client.post('/saved-jobs', { job, status }),

  updateSavedJob: (/** @type {any} */ id, /** @type {any} */ patch) =>
    client.patch(`/saved-jobs/${id}`, patch),

  removeSavedJob: (/** @type {any} */ id) => client.delete(`/saved-jobs/${id}`),

  campusDrives: (/** @type {any} */ params) => client.get('/campus/drives', { params }),

  matchScore: (/** @type {any} */ profile, /** @type {any} */ job) =>
    client.post('/matching/score', { profile, job }),

  skillGap: (/** @type {any} */ profile, /** @type {any} */ job) =>
    client.post('/skills/gap', { profile, job }),

  learningRoadmap: (/** @type {any} */ missing_skills, context = '') =>
    client.post('/learning/roadmap', { missing_skills, context }),

  generateInterview: (/** @type {any} */ role, /** @type {any} */ profile, num_questions = 5) =>
    client.post('/interview/generate', { role, profile, num_questions }),

  chat: (/** @type {any} */ message, /** @type {any} */ profile, session_id = 'default') =>
    client.post('/chat', { message, profile, session_id }),

  analyzeGithub: (/** @type {any} */ username) => client.post('/github/analyze', { username }),
}

export default api
