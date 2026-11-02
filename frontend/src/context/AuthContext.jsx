import { useCallback, useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { AuthContext } from './context.js'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    axios
      .get('/api/auth/me', { withCredentials: true })
      .then((res) => setUser(res.data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const loginWithGoogleToken = useCallback(async (googleIdToken) => {
    const res = await axios.post(
      '/api/auth/google',
      { id_token: googleIdToken },
      { withCredentials: true },
    )
    setUser(res.data.user)
  }, [])

  const logout = useCallback(async () => {
    await axios.post('/api/auth/logout', {}, { withCredentials: true }).catch(() => {})
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, loading, loginWithGoogleToken, logout }),
    [user, loading, loginWithGoogleToken, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
