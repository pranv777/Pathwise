import GoogleLoginButton from './GoogleLoginButton.jsx'

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-paper">
      <div className="panel p-10 flex flex-col items-center gap-6 max-w-sm text-center">
        <div className="w-10 h-10 rounded-md bg-ink flex items-center justify-center">
          <span className="text-white font-display font-semibold">W</span>
        </div>
        <div>
          <h1 className="font-display text-xl font-semibold">Wayfind</h1>
          <p className="text-sm text-muted mt-1">
            Sign in to continue to your placement dashboard.
          </p>
        </div>
        <GoogleLoginButton />
      </div>
    </div>
  )
}
