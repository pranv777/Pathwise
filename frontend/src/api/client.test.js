import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const h = vi.hoisted(() => {
  const state = { request: null, onOk: null, onErr: null }
  const instance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn((fn) => (state.request = fn)) },
      response: {
        use: vi.fn((ok, err) => {
          state.onOk = ok
          state.onErr = err
        }),
      },
    },
  }
  return { state, instance, create: vi.fn(() => instance) }
})

vi.mock('axios', () => ({ default: { create: h.create } }))

const { api } = await import('./client.js')

describe('api client', () => {
  it('creates one instance with cookies and a base URL', () => {
    expect(h.create).toHaveBeenCalledWith(
      expect.objectContaining({ baseURL: '/api', withCredentials: true }),
    )
  })

  it.each([
    ['history', [], 'get', ['/history']],
    ['getProfile', [], 'get', ['/profile']],
    ['savedJobs', [], 'get', ['/saved-jobs']],
    ['deleteMyData', [], 'delete', ['/me/data']],
    ['removeSavedJob', [7], 'delete', ['/saved-jobs/7']],
    ['saveProfile', [{ a: 1 }], 'put', ['/profile', { a: 1 }]],
    [
      'updateSavedJob',
      [7, { status: 'applied' }],
      'patch',
      ['/saved-jobs/7', { status: 'applied' }],
    ],
    ['saveHistory', [{ s: 1 }], 'post', ['/history/snapshot', { s: 1 }]],
    ['saveJob', [{ id: 'j' }], 'post', ['/saved-jobs', { job: { id: 'j' }, status: 'saved' }]],
    [
      'searchJobs',
      ['py', 'Pune'],
      'post',
      ['/jobs/search', { query: 'py', location: 'Pune', limit: 5, job_type: 'any' }],
    ],
    [
      'searchJobs',
      ['py', '', 3, 'internship'],
      'post',
      ['/jobs/search', { query: 'py', location: '', limit: 3, job_type: 'internship' }],
    ],
    ['matchScore', ['P', 'J'], 'post', ['/matching/score', { profile: 'P', job: 'J' }]],
    ['skillGap', ['P', 'J'], 'post', ['/skills/gap', { profile: 'P', job: 'J' }]],
    [
      'learningRoadmap',
      [['Docker']],
      'post',
      ['/learning/roadmap', { missing_skills: ['Docker'], context: '' }],
    ],
    [
      'generateInterview',
      ['SWE', 'P'],
      'post',
      ['/interview/generate', { role: 'SWE', profile: 'P', num_questions: 5 }],
    ],
    [
      'chat',
      ['hi', 'P'],
      'post',
      ['/chat', { message: 'hi', profile: 'P', session_id: 'default' }],
    ],
    ['analyzeGithub', ['octocat'], 'post', ['/github/analyze', { username: 'octocat' }]],
    [
      'campusDrives',
      [{ job_type: 'any' }],
      'get',
      ['/campus/drives', { params: { job_type: 'any' } }],
    ],
  ])('%s calls the right endpoint', (method, args, verb, expected) => {
    api[method](...args)
    expect(h.instance[verb]).toHaveBeenLastCalledWith(...expected)
  })

  it('uploadResume sends multipart form data', () => {
    const file = new File(['x'], 'cv.txt', { type: 'text/plain' })
    api.uploadResume(file)
    const [url, body, config] = h.instance.post.mock.calls.at(-1)
    expect(url).toBe('/resume/upload')
    expect(body).toBeInstanceOf(FormData)
    expect(body.get('file')).toBe(file)
    expect(config.headers['Content-Type']).toBe('multipart/form-data')
  })
})

describe('slow-request detection', () => {
  let events
  const listener = (e) => events.push(e.detail)

  beforeEach(() => {
    vi.useFakeTimers()
    events = []
    window.addEventListener('wayfind:slow', listener)
  })

  afterEach(() => {
    window.removeEventListener('wayfind:slow', listener)
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('announces a slow request after 4s and clears it when it finishes', () => {
    const config = h.state.request({})
    vi.advanceTimersByTime(3999)
    expect(events).toEqual([])
    vi.advanceTimersByTime(1)
    expect(events).toEqual([true])
    h.state.onOk({ config })
    expect(events).toEqual([true, false])
  })

  it('stays silent for fast requests', () => {
    const config = h.state.request({})
    vi.advanceTimersByTime(1000)
    h.state.onOk({ config })
    vi.advanceTimersByTime(10000)
    expect(events).toEqual([])
  })

  it('keeps announcing until the last slow request ends', () => {
    const a = h.state.request({})
    const b = h.state.request({})
    vi.advanceTimersByTime(4000)
    h.state.onOk({ config: a })
    expect(events.at(-1)).toBe(true)
    h.state.onOk({ config: b })
    expect(events.at(-1)).toBe(false)
  })

  it('clears the slow state when a request fails', async () => {
    const config = h.state.request({})
    vi.advanceTimersByTime(4000)
    await expect(h.state.onErr({ config, response: { status: 500 } })).rejects.toBeDefined()
    expect(events.at(-1)).toBe(false)
  })

  it('reloads on 401 only', async () => {
    const reload = vi.fn()
    vi.stubGlobal('location', { reload })
    await expect(
      h.state.onErr({ config: h.state.request({}), response: { status: 500 } }),
    ).rejects.toBeDefined()
    expect(reload).not.toHaveBeenCalled()
    await expect(
      h.state.onErr({ config: h.state.request({}), response: { status: 401 } }),
    ).rejects.toBeDefined()
    expect(reload).toHaveBeenCalledTimes(1)
  })
})
