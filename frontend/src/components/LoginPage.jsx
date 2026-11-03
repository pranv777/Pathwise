import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { useAuth } from '../context/useAuth.js'
import { friendlyError } from '../utils/errors.js'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const RESEND_SECONDS = 60

function Field({ label, ...props }) {
  return (
    <label className="block text-left text-xs text-muted space-y-1">
      {label}
      <input
        {...props}
        className="w-full text-sm px-3 py-2.5 rounded-md border border-hairline bg-white text-ink outline-none focus:border-cobalt"
      />
    </label>
  )
}

export default function LoginPage() {
  const { login, register, resendOtp, verifyOtp } = useAuth()
  const [mode, setMode] = useState('login') // 'login' | 'signup' | 'verify'
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' })
  const [otp, setOtp] = useState('')
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [busy, setBusy] = useState(false)
  const [cooldown, setCooldown] = useState(0)

  useEffect(() => {
    if (cooldown <= 0) return
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000)
    return () => clearTimeout(t)
  }, [cooldown])

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))

  const switchMode = (next) => {
    setMode(next)
    setError('')
    setInfo('')
  }

  const run = async (action, fallback) => {
    setError('')
    setInfo('')
    setBusy(true)
    try {
      await action()
    } catch (err) {
      setError(friendlyError(err, fallback))
    } finally {
      setBusy(false)
    }
  }

  const submitLogin = (e) => {
    e.preventDefault()
    if (!EMAIL_RE.test(form.email.trim())) return setError('Enter a valid email address.')
    if (!form.password) return setError('Enter your password.')
    run(() => login(form.email.trim(), form.password), 'Could not sign in.')
  }

  const submitSignup = (e) => {
    e.preventDefault()
    if (!form.name.trim()) return setError('Enter your name.')
    if (!EMAIL_RE.test(form.email.trim())) return setError('Enter a valid email address.')
    if (form.password.length < 8) return setError('Password must be at least 8 characters.')
    if (form.password !== form.confirm) return setError('Passwords do not match.')
    run(async () => {
      await register(form.name.trim(), form.email.trim(), form.password)
      setOtp('')
      setCooldown(RESEND_SECONDS)
      setMode('verify')
    }, 'Could not create your account.')
  }

  const submitOtp = (e) => {
    e.preventDefault()
    if (!/^\d{6}$/.test(otp)) return setError('Enter the 6-digit code from your email.')
    run(() => verifyOtp(form.email.trim(), otp), 'Could not verify the code.')
  }

  const resend = () =>
    run(async () => {
      await resendOtp(form.email.trim())
      setCooldown(RESEND_SECONDS)
      setInfo('A new code has been sent.')
    }, 'Could not resend the code.')

  const submitButton = (label) => (
    <button type="submit" className="btn-primary w-full justify-center" disabled={busy}>
      {busy && <Loader2 size={16} className="animate-spin" />}
      {label}
    </button>
  )

  return (
    <div className="min-h-screen flex items-center justify-center bg-paper px-4">
      <div className="panel p-8 w-full max-w-sm space-y-6 text-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-md bg-ink flex items-center justify-center">
            <span className="text-white font-display font-semibold">W</span>
          </div>
          <div>
            <h1 className="font-display text-xl font-semibold">Wayfind</h1>
            <p className="text-sm text-muted mt-1">
              {mode === 'login' && 'Sign in to continue to your placement dashboard.'}
              {mode === 'signup' && 'Create your account.'}
              {mode === 'verify' && 'Verify your email.'}
            </p>
          </div>
        </div>

        {mode === 'login' && (
          <form onSubmit={submitLogin} className="space-y-3" noValidate>
            <Field
              label="Email"
              type="email"
              autoComplete="email"
              value={form.email}
              onChange={set('email')}
            />
            <Field
              label="Password"
              type="password"
              autoComplete="current-password"
              maxLength={72}
              value={form.password}
              onChange={set('password')}
            />
            {submitButton('Sign in')}
          </form>
        )}

        {mode === 'signup' && (
          <form onSubmit={submitSignup} className="space-y-3" noValidate>
            <Field
              label="Name"
              autoComplete="name"
              maxLength={100}
              value={form.name}
              onChange={set('name')}
            />
            <Field
              label="Email"
              type="email"
              autoComplete="email"
              value={form.email}
              onChange={set('email')}
            />
            <Field
              label="Password (8+ characters)"
              type="password"
              autoComplete="new-password"
              maxLength={72}
              value={form.password}
              onChange={set('password')}
            />
            <Field
              label="Confirm password"
              type="password"
              autoComplete="new-password"
              maxLength={72}
              value={form.confirm}
              onChange={set('confirm')}
            />
            {submitButton('Create account')}
          </form>
        )}

        {mode === 'verify' && (
          <form onSubmit={submitOtp} className="space-y-3" noValidate>
            <p className="text-sm text-muted">
              We sent a 6-digit code to <span className="text-ink font-medium">{form.email}</span>.
              It expires in 10 minutes.
            </p>
            <Field
              label="Verification code"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
              placeholder="123456"
            />
            {submitButton('Verify and create account')}
            <div className="flex items-center justify-between text-xs">
              <button
                type="button"
                onClick={resend}
                disabled={busy || cooldown > 0}
                className="text-cobalt-dark disabled:text-muted"
              >
                {cooldown > 0 ? `Resend code in ${cooldown}s` : 'Resend code'}
              </button>
              <button type="button" onClick={() => switchMode('signup')} className="text-muted">
                Use a different email
              </button>
            </div>
          </form>
        )}

        {error && (
          <p role="alert" className="text-sm text-signal-red">
            {error}
          </p>
        )}
        {info && <p className="text-sm text-signal-green">{info}</p>}

        {mode !== 'verify' && (
          <p className="text-sm text-muted">
            {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
            <button
              type="button"
              onClick={() => switchMode(mode === 'login' ? 'signup' : 'login')}
              className="text-cobalt-dark font-medium"
            >
              {mode === 'login' ? 'Create one' : 'Sign in'}
            </button>
          </p>
        )}
      </div>
    </div>
  )
}
