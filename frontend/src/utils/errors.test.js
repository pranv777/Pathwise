import { describe, expect, it } from 'vitest'
import { friendlyError } from './errors'

const http = (status, data = {}) => ({ response: { status, data } })

describe('friendlyError', () => {
  it.each(['ECONNABORTED', 'ETIMEDOUT'])('explains a timeout (%s)', (code) => {
    expect(friendlyError({ code })).toMatch(/taking longer than expected/)
  })

  it('reports an unreachable server when a request was sent but nothing came back', () => {
    expect(friendlyError({ request: {} })).toMatch(/Can't reach the server/)
  })

  it('uses the fallback when the request never left (no response, no request)', () => {
    expect(friendlyError(new Error('boom'), 'fallback')).toBe('fallback')
    expect(friendlyError(undefined)).toBe('Something went wrong. Please try again.')
  })

  it('handles 429 before anything else', () => {
    expect(friendlyError(http(429, { detail: 'slow down' }))).toMatch(/Too many requests/)
  })

  it('hides the detail of 5xx errors', () => {
    expect(friendlyError(http(500, { detail: 'Traceback...' }))).toMatch(/busy or had a problem/)
    expect(friendlyError(http(503))).toMatch(/busy or had a problem/)
  })

  it('shows a string detail for 4xx errors, even on 401/413/422', () => {
    expect(friendlyError(http(400, { detail: 'Unsupported file type' }))).toBe(
      'Unsupported file type',
    )
    expect(friendlyError(http(422, { detail: 'Could not extract text' }))).toBe(
      'Could not extract text',
    )
  })

  it.each([
    [401, /session expired/],
    [413, /too large/],
    [422, /invalid or too long/],
  ])('has default text for %i without a detail', (status, pattern) => {
    expect(friendlyError(http(status))).toMatch(pattern)
    expect(friendlyError(http(status, { detail: [{ msg: 'x' }] }))).toMatch(pattern)
  })

  it('falls back for other statuses', () => {
    expect(friendlyError(http(404), 'Nope')).toBe('Nope')
  })
})
