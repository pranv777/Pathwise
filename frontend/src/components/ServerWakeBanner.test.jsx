import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ServerWakeBanner from './ServerWakeBanner'

beforeEach(() => vi.useFakeTimers())
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('ServerWakeBanner', () => {
  it('stays hidden when the health check is quick', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({}))
    render(<ServerWakeBanner />)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000)
    })
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('appears when the health check is slow and disappears when it finishes', async () => {
    /** @type {(value: object) => void} */
    let finish = () => {}
    vi.stubGlobal(
      'fetch',
      vi.fn(() => new Promise((r) => (finish = r))),
    )
    render(<ServerWakeBanner />)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(4100)
    })
    expect(screen.getByRole('status')).toHaveTextContent('Waking up the server')
    await act(async () => finish({}))
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('also finishes when the health check fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    render(<ServerWakeBanner />)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000)
    })
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('reacts to slow API calls reported by the client', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({}))
    render(<ServerWakeBanner />)
    await act(async () => {
      window.dispatchEvent(new CustomEvent('pathwise:slow', { detail: true }))
    })
    expect(screen.getByRole('status')).toBeInTheDocument()
    await act(async () => {
      window.dispatchEvent(new CustomEvent('pathwise:slow', { detail: false }))
    })
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })
})
