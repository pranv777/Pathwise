import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'

// Shows a banner if /api/health (warm-up ping) or any API call takes longer than SLOW_MS.
const SLOW_MS = 4000

export default function ServerWakeBanner() {
  const [warming, setWarming] = useState(false) // initial warm-up ping
  const [slowCalls, setSlowCalls] = useState(false) // from api.js interceptor

  useEffect(() => {
    let done = false
    const timer = setTimeout(() => !done && setWarming(true), SLOW_MS)
    fetch('/api/health')
      .catch(() => {})
      .finally(() => {
        done = true
        clearTimeout(timer)
        setWarming(false)
      })
    const onSlow = (e) => setSlowCalls(Boolean(e.detail))
    window.addEventListener('wayfind:slow', onSlow)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('wayfind:slow', onSlow)
    }
  }, [])

  if (!warming && !slowCalls) return null
  return (
    <div
      role="status"
      className="flex items-center gap-2 px-4 py-2 text-sm bg-cobalt-light text-cobalt-dark border-b border-hairline"
    >
      <Loader2 size={14} className="animate-spin shrink-0" />
      Waking up the server… the first request can take up to a minute. Hang tight.
    </div>
  )
}
