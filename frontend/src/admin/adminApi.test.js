import { beforeEach, describe, expect, it, vi } from 'vitest'

const h = vi.hoisted(() => {
  const instance = { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() }
  return { instance, create: vi.fn(() => instance) }
})

vi.mock('axios', () => ({ default: { create: h.create } }))

const { adminApi, errMsg } = await import('./adminApi.js')

beforeEach(() => {
  for (const fn of Object.values(h.instance)) fn.mockReset().mockResolvedValue({ data: 'ok' })
})

describe('adminApi', () => {
  it('uses its own instance with cookies', () => {
    expect(h.create).toHaveBeenCalledWith(
      expect.objectContaining({ baseURL: '/api/admin', withCredentials: true }),
    )
  })

  it.each([
    ['overview', [7], 'get', ['/overview', { params: { days: 7 } }]],
    ['overview', [], 'get', ['/overview', { params: { days: 14 } }]],
    ['students', [{ q: 'a' }], 'get', ['/students', { params: { q: 'a' } }]],
    ['student', [3], 'get', ['/students/3']],
    ['drives', [], 'get', ['/drives']],
    ['agents', [], 'get', ['/agents']],
    ['runs', [{ kind: 'mcp' }], 'get', ['/runs', { params: { kind: 'mcp' } }]],
    ['kb', [], 'get', ['/kb']],
    ['mcp', [], 'get', ['/mcp']],
    ['audit', [{ action: 'kb' }], 'get', ['/audit', { params: { action: 'kb' } }]],
  ])('%s calls GET and unwraps the data', async (name, args, verb, expected) => {
    expect(await adminApi[name](...args)).toBe('ok')
    expect(h.instance[verb]).toHaveBeenCalledWith(...expected)
  })

  it('updates a student status', async () => {
    await adminApi.setStudentStatus(3, 'suspended')
    expect(h.instance.patch).toHaveBeenCalledWith('/students/3/status', { status: 'suspended' })
  })

  it('deletes students, drives and KB sources', async () => {
    await adminApi.deleteStudent(3)
    await adminApi.deleteDrive('drive-1')
    await adminApi.kbDelete('a.txt')
    expect(h.instance.delete).toHaveBeenCalledWith('/students/3')
    expect(h.instance.delete).toHaveBeenCalledWith('/drives/drive-1')
    expect(h.instance.delete).toHaveBeenCalledWith('/kb', { params: { source: 'a.txt' } })
  })

  it('builds the CSV export URL from the filters', () => {
    expect(adminApi.studentsCsvUrl({ status: 'active', q: 'a b' })).toBe(
      '/api/admin/students/export.csv?status=active&q=a+b',
    )
  })

  it('creates a drive without an id and updates one with an id', async () => {
    await adminApi.saveDrive({ company: 'Acme' })
    expect(h.instance.post).toHaveBeenCalledWith('/drives', { company: 'Acme' })
    await adminApi.saveDrive({ id: 'drive-2', company: 'Acme' })
    expect(h.instance.put).toHaveBeenCalledWith('/drives/drive-2', {
      id: 'drive-2',
      company: 'Acme',
    })
  })

  it('uploads a KB file as multipart form data', async () => {
    const file = new File(['hi'], 'a.txt', { type: 'text/plain' })
    await adminApi.kbUpload('career_guide', file)
    const [url, body, config] = h.instance.post.mock.calls[0]
    expect(url).toBe('/kb')
    expect(body.get('file')).toBe(file)
    expect(config.params).toEqual({ doc_type: 'career_guide' })
    expect(config.timeout).toBe(120000)
  })

  it('re-seeds with a long timeout', async () => {
    await adminApi.kbReseed()
    expect(h.instance.post).toHaveBeenCalledWith('/kb/reseed', null, { timeout: 120000 })
  })

  it('turns errors into friendly messages', () => {
    expect(typeof errMsg(new Error('boom'))).toBe('string')
  })
})
