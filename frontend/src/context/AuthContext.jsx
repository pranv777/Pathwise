import { useCallback, useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { AuthContext } from './context.js'

const opts = { withCredentials: true }

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    axios
      .get('/api/auth/me', opts)
      .then((res) => setUser(res.data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email, password) => {
    const res = await axios.post('/api/auth/login', { email, password }, opts)
    setUser(res.data.user)
  }, [])

  // Step 1 of sign-up: sends the code. The account is created by verifyOtp.
  const register = useCallback(
    (name, email, password) => axios.post('/api/auth/register', { name, email, password }, opts),
    [],
  )

  const resendOtp = useCallback((email) => axios.post('/api/auth/resend-otp', { email }, opts), [])

  const verifyOtp = useCallback(async (email, otp) => {
    const res = await axios.post('/api/auth/verify-otp', { email, otp }, opts)
    setUser(res.data.user)
  }, [])

  const logout = useCallback(async () => {
    await axios.post('/api/auth/logout', {}, opts).catch(() => {})
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, loading, login, register, resendOtp, verifyOtp, logout }),
    [user, loading, login, register, resendOtp, verifyOtp, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
