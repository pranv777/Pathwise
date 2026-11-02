import { useState } from 'react'
import { Trash2, Loader2 } from 'lucide-react'
import { friendlyError } from '../utils/errors'

export default function DeleteDataButton({ onDelete }) {
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const run = async () => {
    setBusy(true)
    setError('')
    try {
      await onDelete()
      setConfirming(false)
    } catch (err) {
      setError(friendlyError(err, 'Could not delete your data.'))
    } finally {
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
        <Trash2 size={13} /> Delete my data
      </button>
    )
  }

  return (
    <div className="panel p-4 space-y-3 max-w-sm">
      <p className="text-sm">
        This permanently deletes your saved resume data and your history. Your account stays. This
        can&apos;t be undone.
      </p>
      {error && <p className="text-xs text-signal-red">{error}</p>}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={run}
          disabled={busy}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-signal-red text-white text-sm font-medium disabled:opacity-60"
        >
          {busy && <Loader2 size={13} className="animate-spin" />}
          Yes, delete everything
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
    </div>
  )
}
