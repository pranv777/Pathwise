import { useState } from 'react'
import { Trash2, Loader2 } from 'lucide-react'
import api from '../api/client.js'
import { friendlyError } from '../utils/errors.js'

export default function DeleteAccountButton({ onDeleted }) {
  const [confirming, setConfirming] = useState(false)
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const run = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.deleteAccount(password)
      await onDeleted()
    } catch (err) {
      setError(friendlyError(err, 'Could not delete your account.'))
      setBusy(false)
    }
  }

  if (!confirming) {
    return (
      <button
        type="button"
        onClick={() => setConfirming(true)}
        className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-signal-red"
      >
        <Trash2 size={13} /> Delete my account
      </button>
    )
  }

  return (
    <form onSubmit={run} className="panel p-4 space-y-3 max-w-sm">
      <p className="text-sm">
        This permanently deletes your account, resume data and history. This can&apos;t be undone.
        Enter your password to confirm.
      </p>
      <input
        type="password"
        required
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
        className="w-full text-sm px-3 py-2 rounded-md border border-hairline focus:border-cobalt outline-none"
      />
      {error && <p className="text-xs text-signal-red">{error}</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={busy || !password}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-signal-red text-white text-sm font-medium disabled:opacity-60"
        >
          {busy && <Loader2 size={13} className="animate-spin" />}
          Delete my account
        </button>
        <button
          type="button"
          onClick={() => setConfirming(false)}
          disabled={busy}
          className="px-3 py-1.5 rounded-md border border-hairline text-sm"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
