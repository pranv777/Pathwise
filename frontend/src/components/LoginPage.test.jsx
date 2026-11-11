import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const auth = vi.hoisted(() => ({
  login: vi.fn(),
  register: vi.fn(),
  resendOtp: vi.fn(),
  verifyOtp: vi.fn(),
  forgotPassword: vi.fn(),
  resetPassword: vi.fn(),
}))
vi.mock('../context/useAuth.js', () => ({ useAuth: () => auth }))

import LoginPage from './LoginPage'

beforeEach(() => {
  vi.clearAllMocks()
  for (const fn of Object.values(auth)) fn.mockResolvedValue(undefined)
})

const type = (user, label, text) => user.type(screen.getByLabelText(label), text)

async function openSignup(user) {
  await user.click(screen.getByRole('button', { name: 'Create one' }))
}

async function fillSignup(user, overrides = {}) {
  const v = { name: 'Asha', email: 'asha@example.com', pw: 'longenough', confirm: 'longenough' }
  Object.assign(v, overrides)
  if (v.name) await type(user, 'Name', v.name)
  if (v.email) await type(user, 'Email', v.email)
  if (v.pw) await type(user, 'Password (8+ characters)', v.pw)
  if (v.confirm) await type(user, 'Confirm password', v.confirm)
}

async function reachVerify(user) {
  await openSignup(user)
  await fillSignup(user)
  await user.click(screen.getByRole('button', { name: 'Create account' }))
  await screen.findByText('Verify your email.')
}

describe('LoginPage: sign in', () => {
  it('validates the email and password before calling the API', async () => {
    const user = userEvent.setup()
    render(<LoginPage />)
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Enter a valid email address.')
    await type(user, 'Email', 'a@b.co')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Enter your password.')
    expect(auth.login).not.toHaveBeenCalled()
  })

  it('signs in with trimmed credentials', async () => {
    const user = userEvent.setup()
    render(<LoginPage />)
    await type(user, 'Email', ' a@b.co ')
    await type(user, 'Password', 'secret')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    await waitFor(() => expect(auth.login).toHaveBeenCalledWith('a@b.co', 'secret'))
  })

  it('shows the server message when sign in fails', async () => {
    auth.login.mockRejectedValue({ response: { status: 401, data: { detail: 'Incorrect.' } } })
    const user = userEvent.setup()
    render(<LoginPage />)
    await type(user, 'Email', 'a@b.co')
    await type(user, 'Password', 'x')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect.')
  })

  it('falls back to a generic message', async () => {
    auth.login.mockRejectedValue(new Error('x'))
    const user = userEvent.setup()
    render(<LoginPage />)
    await type(user, 'Email', 'a@b.co')
    await type(user, 'Password', 'x')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not sign in.')
  })

  it('switches between sign in and sign up and clears errors', async () => {
    const user = userEvent.setup()
    render(<LoginPage />)
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(screen.getByRole('alert')).toBeInTheDocument()
    await openSignup(user)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByText('Create your account.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(screen.getByText(/Sign in to continue/)).toBeInTheDocument()
  })
})

describe('LoginPage: sign up', () => {
  it.each([
    [{ name: '' }, 'Enter your name.'],
    [{ email: 'nope' }, 'Enter a valid email address.'],
    [{ pw: 'short', confirm: 'short' }, 'Password must be at least 8 characters.'],
    [{ confirm: 'different1' }, 'Passwords do not match.'],
  ])('rejects invalid input %#', async (overrides, message) => {
    const user = userEvent.setup()
    render(<LoginPage />)
    await openSignup(user)
    await fillSignup(user, overrides)
    await user.click(screen.getByRole('button', { name: 'Create account' }))
    expect(screen.getByRole('alert')).toHaveTextContent(message)
    expect(auth.register).not.toHaveBeenCalled()
  })

  it('registers and moves to the verification step', async () => {
    const user = userEvent.setup()
    render(<LoginPage />)
    await reachVerify(user)
    expect(auth.register).toHaveBeenCalledWith('Asha', 'asha@example.com', 'longenough')
    expect(screen.getByText('asha@example.com')).toBeInTheDocument()
  })

  it('reports registration failures', async () => {
    auth.register.mockRejectedValue(new Error('x'))
    const user = userEvent.setup()
    render(<LoginPage />)
    await openSignup(user)
    await fillSignup(user)
    await user.click(screen.getByRole('button', { name: 'Create account' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not create your account.')
  })
})

describe('LoginPage: verification', () => {
  it('accepts only 6 digits and strips other characters', async () => {
    const user = userEvent.setup()
    render(<LoginPage />)
    await reachVerify(user)
    const code = screen.getByLabelText('Verification code')
    await user.type(code, '12ab34')
    expect(code).toHaveValue('1234')
    await user.click(screen.getByRole('button', { name: 'Verify and create account' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Enter the 6-digit code from your email.')
    await user.type(code, '56')
    await user.click(screen.getByRole('button', { name: 'Verify and create account' }))
    await waitFor(() => expect(auth.verifyOtp).toHaveBeenCalledWith('asha@example.com', '123456'))
  })

  it('reports verification failures', async () => {
    auth.verifyOtp.mockRejectedValue(new Error('x'))
    const user = userEvent.setup()
    render(<LoginPage />)
    await reachVerify(user)
    await user.type(screen.getByLabelText('Verification code'), '123456')
    await user.click(screen.getByRole('button', { name: 'Verify and create account' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not verify the code.')
  })

  it('starts a resend cooldown and can go back to sign up', async () => {
    const user = userEvent.setup()
    render(<LoginPage />)
    await reachVerify(user)
    expect(screen.getByRole('button', { name: /Resend code in \d+s/ })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Use a different email' }))
    expect(screen.getByText('Create your account.')).toBeInTheDocument()
  })

  it('resends the code once the cooldown is over', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      render(<LoginPage />)
      await reachVerify(user)
      await vi.advanceTimersByTimeAsync(61000)
      await user.click(await screen.findByRole('button', { name: 'Resend code' }))
      await waitFor(() => expect(auth.resendOtp).toHaveBeenCalledWith('asha@example.com'))
      expect(await screen.findByText('A new code has been sent.')).toBeInTheDocument()
    } finally {
      vi.useRealTimers()
    }
  })

  it('reports resend failures', async () => {
    auth.resendOtp.mockRejectedValue(new Error('x'))
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      render(<LoginPage />)
      await reachVerify(user)
      await vi.advanceTimersByTimeAsync(61000)
      await user.click(await screen.findByRole('button', { name: 'Resend code' }))
      expect(await screen.findByRole('alert')).toHaveTextContent('Could not resend the code.')
    } finally {
      vi.useRealTimers()
    }
  })
})

describe('LoginPage: password reset', () => {
  async function reachReset(user) {
    await user.click(screen.getByRole('button', { name: 'Forgot password?' }))
    await type(user, 'Email', 'asha@example.com')
    await user.click(screen.getByRole('button', { name: 'Send reset code' }))
    await screen.findByText('Choose a new password.')
  }

  it('validates the email before sending a code', async () => {
    const user = userEvent.setup()
    render(<LoginPage />)
    await user.click(screen.getByRole('button', { name: 'Forgot password?' }))
    await user.click(screen.getByRole('button', { name: 'Send reset code' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Enter a valid email address.')
    expect(auth.forgotPassword).not.toHaveBeenCalled()
  })

  it('reports a failure to send the code', async () => {
    auth.forgotPassword.mockRejectedValue(new Error('x'))
    const user = userEvent.setup()
    render(<LoginPage />)
    await user.click(screen.getByRole('button', { name: 'Forgot password?' }))
    await type(user, 'Email', 'asha@example.com')
    await user.click(screen.getByRole('button', { name: 'Send reset code' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not send the code.')
  })

  it('sends a code and then resets the password', async () => {
    const user = userEvent.setup()
    render(<LoginPage />)
    await reachReset(user)
    expect(screen.getByText(/we sent a 6-digit code/)).toBeInTheDocument()
    await type(user, 'Reset code', '123456')
    await type(user, 'New password (8+ characters)', 'brandnewpass')
    await type(user, 'Confirm new password', 'brandnewpass')
    await user.click(screen.getByRole('button', { name: 'Reset password' }))
    await waitFor(() =>
      expect(auth.resetPassword).toHaveBeenCalledWith('asha@example.com', '123456', 'brandnewpass'),
    )
    expect(await screen.findByText(/Password updated/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
  })

  it.each([
    [{ code: '123', pw: 'brandnewpass', confirm: 'brandnewpass' }, 'Enter the 6-digit code'],
    [{ code: '123456', pw: 'short', confirm: 'short' }, 'at least 8 characters'],
    [{ code: '123456', pw: 'brandnewpass', confirm: 'other-pass1' }, 'Passwords do not match.'],
  ])('rejects invalid reset input %#', async (v, message) => {
    const user = userEvent.setup()
    render(<LoginPage />)
    await reachReset(user)
    await type(user, 'Reset code', v.code)
    await type(user, 'New password (8+ characters)', v.pw)
    await type(user, 'Confirm new password', v.confirm)
    await user.click(screen.getByRole('button', { name: 'Reset password' }))
    expect(screen.getByRole('alert')).toHaveTextContent(message)
    expect(auth.resetPassword).not.toHaveBeenCalled()
  })

  it('reports a failed reset', async () => {
    auth.resetPassword.mockRejectedValue(new Error('x'))
    const user = userEvent.setup()
    render(<LoginPage />)
    await reachReset(user)
    await type(user, 'Reset code', '123456')
    await type(user, 'New password (8+ characters)', 'brandnewpass')
    await type(user, 'Confirm new password', 'brandnewpass')
    await user.click(screen.getByRole('button', { name: 'Reset password' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not reset your password.')
  })

  it('can resend the reset code after the cooldown and go back to sign in', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      render(<LoginPage />)
      await reachReset(user)
      await vi.advanceTimersByTimeAsync(61000)
      await user.click(await screen.findByRole('button', { name: 'Resend code' }))
      expect(await screen.findByText(/we sent a new code/)).toBeInTheDocument()
      await user.click(screen.getByRole('button', { name: 'Back to sign in' }))
      expect(screen.getByText(/Sign in to continue/)).toBeInTheDocument()
    } finally {
      vi.useRealTimers()
    }
  })

  it('reports a failed resend', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      render(<LoginPage />)
      await reachReset(user)
      auth.forgotPassword.mockRejectedValue(new Error('x'))
      await vi.advanceTimersByTimeAsync(61000)
      await user.click(await screen.findByRole('button', { name: 'Resend code' }))
      expect(await screen.findByRole('alert')).toHaveTextContent('Could not resend the code.')
    } finally {
      vi.useRealTimers()
    }
  })
})
