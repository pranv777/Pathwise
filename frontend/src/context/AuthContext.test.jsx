import { act, renderHook, waitFor } from '@testing-library/react'
import axios from 'axios'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from './AuthContext'
import { useAuth } from './useAuth'

vi.mock('axios', () => ({ default: { get: vi.fn(), post: vi.fn() } }))
const mockAxios = /** @type {any} */ (axios)

const ana = { id: 1, name: 'Ana', email: 'ana@example.com' }

const setup = async () => {
  const hook = renderHook(() => useAuth(), { wrapper: AuthProvider })
  await waitFor(() => expect(hook.result.current.loading).toBe(false))
  return hook
}

describe('AuthProvider', () => {
  beforeEach(() => {
    mockAxios.get.mockReset()
    mockAxios.post.mockReset()
  })

  it('starts loading, then exposes the signed-in user', async () => {
    mockAxios.get.mockResolvedValue({ data: ana })
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })
    expect(result.current.loading).toBe(true)
    await waitFor(() => expect(result.current.user).toEqual(ana))
    expect(result.current.loading).toBe(false)
    expect(mockAxios.get).toHaveBeenCalledWith('/api/auth/me', { withCredentials: true })
  })

  it('has no user when the session is invalid', async () => {
    mockAxios.get.mockRejectedValue({ response: { status: 401 } })
    const { result } = await setup()
    expect(result.current.user).toBeNull()
  })

  it('logs in with email and password', async () => {
    mockAxios.get.mockRejectedValue(new Error('401'))
    mockAxios.post.mockResolvedValue({ data: { user: ana } })
    const { result } = await setup()

    await act(async () => {
      await result.current.login('ana@example.com', 'secret123')
    })

    expect(mockAxios.post).toHaveBeenCalledWith(
      '/api/auth/login',
      { email: 'ana@example.com', password: 'secret123' },
      { withCredentials: true },
    )
    expect(result.current.user).toEqual(ana)
  })

  it('creates the account only after the OTP is verified', async () => {
    mockAxios.get.mockRejectedValue(new Error('401'))
    mockAxios.post.mockResolvedValueOnce({ data: { status: 'otp_sent' } })
    mockAxios.post.mockResolvedValueOnce({ data: { user: ana } })
    const { result } = await setup()

    await act(async () => {
      await result.current.register('Ana', 'ana@example.com', 'secret123')
    })
    expect(result.current.user).toBeNull() // not signed in yet

    await act(async () => {
      await result.current.verifyOtp('ana@example.com', '123456')
    })
    expect(mockAxios.post).toHaveBeenLastCalledWith(
      '/api/auth/verify-otp',
      { email: 'ana@example.com', otp: '123456' },
      { withCredentials: true },
    )
    expect(result.current.user).toEqual(ana)
  })

  it('logs out and clears the user', async () => {
    mockAxios.get.mockResolvedValue({ data: ana })
    mockAxios.post.mockResolvedValue({})
    const { result } = await setup()

    await act(async () => {
      await result.current.logout()
    })

    expect(mockAxios.post).toHaveBeenCalledWith('/api/auth/logout', {}, { withCredentials: true })
    expect(result.current.user).toBeNull()
  })

  it('still logs out locally if the server call fails', async () => {
    mockAxios.get.mockResolvedValue({ data: ana })
    mockAxios.post.mockRejectedValue(new Error('offline'))
    const { result } = await setup()

    await act(async () => {
      await result.current.logout()
    })

    expect(result.current.user).toBeNull()
  })
})
