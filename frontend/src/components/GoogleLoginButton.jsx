import { useEffect, useRef } from 'react'
import { useAuth } from '../context/useAuth.js'

const POLL_MS = 100
const MAX_ATTEMPTS = 100 // ~10s for the async GSI script to load

export default function GoogleLoginButton() {
  const buttonRef = useRef(null)
  const { loginWithGoogleToken } = useAuth()
  const loginRef = useRef(loginWithGoogleToken)

  useEffect(() => {
    loginRef.current = loginWithGoogleToken
  }, [loginWithGoogleToken])

  useEffect(() => {
    let cancelled = false
    let timer
    let attempts = 0

    const init = () => {
      if (cancelled) return
      // The GSI script is loaded async/defer and may not be ready on first render.
      if (!window.google?.accounts?.id || !buttonRef.current) {
        if (attempts++ < MAX_ATTEMPTS) timer = setTimeout(init, POLL_MS)
        return
      }
      window.google.accounts.id.initialize({
        client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
        callback: async (response) => {
          await loginRef.current(response.credential)
        },
      })
      window.google.accounts.id.renderButton(buttonRef.current, {
        theme: 'outline',
        size: 'large',
        shape: 'pill',
        text: 'continue_with',
      })
    }

    init()
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [])

  return <div ref={buttonRef} />
}
