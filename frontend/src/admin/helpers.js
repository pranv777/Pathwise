import { useEffect, useState } from 'react'

export function useLoad(fn, deps = []) {
  const [tick, setTick] = useState(0)
  const [result, setResult] = useState({ key: '', data: null, error: null })
  const key = JSON.stringify([...deps, tick])

  useEffect(() => {
    let alive = true
    fn()
      .then((data) => alive && setResult({ key, data, error: null }))
      .catch((error) => alive && setResult({ key, data: null, error }))
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  return {
    data: result.data,
    error: result.error,
    loading: result.key !== key,
    reload: () => setTick((t) => t + 1),
  }
}

export const fmtDate = (v) => (v ? new Date(v).toLocaleString() : '—')
