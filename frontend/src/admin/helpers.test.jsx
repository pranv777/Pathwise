import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { fmtDate, useLoad } from './helpers'

describe('fmtDate', () => {
  it('shows a dash for empty values', () => {
    expect(fmtDate(null)).toBe('—')
    expect(fmtDate('')).toBe('—')
  })

  it('formats real dates', () => {
    expect(fmtDate('2026-01-02T03:04:05Z')).toBe(new Date('2026-01-02T03:04:05Z').toLocaleString())
  })
})

describe('useLoad', () => {
  it('loads data and clears the loading flag', async () => {
    const fn = vi.fn().mockResolvedValue({ n: 1 })
    const { result } = renderHook(() => useLoad(fn))
    expect(result.current.loading).toBe(true)
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.data).toEqual({ n: 1 })
    expect(result.current.error).toBeNull()
  })

  it('exposes errors', async () => {
    const boom = new Error('boom')
    const { result } = renderHook(() => useLoad(() => Promise.reject(boom)))
    await waitFor(() => expect(result.current.error).toBe(boom))
    expect(result.current.data).toBeNull()
  })

  it('reloads on demand', async () => {
    const fn = vi.fn().mockResolvedValue('x')
    const { result } = renderHook(() => useLoad(fn))
    await waitFor(() => expect(result.current.loading).toBe(false))
    act(() => result.current.reload())
    await waitFor(() => expect(fn).toHaveBeenCalledTimes(2))
  })

  it('refetches when its dependencies change', async () => {
    const fn = vi.fn().mockResolvedValue('x')
    const { rerender } = renderHook(({ q }) => useLoad(fn, [q]), { initialProps: { q: 'a' } })
    await waitFor(() => expect(fn).toHaveBeenCalledTimes(1))
    rerender({ q: 'b' })
    await waitFor(() => expect(fn).toHaveBeenCalledTimes(2))
  })

  it('ignores a response that arrives after unmount', async () => {
    /** @type {(value: string) => void} */
    let resolve = () => {}
    const fn = () => new Promise((r) => (resolve = r))
    const { result, unmount } = renderHook(() => useLoad(fn))
    unmount()
    await act(async () => resolve('late'))
    expect(result.current.data).toBeNull()
  })
})
