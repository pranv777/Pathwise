export function friendlyError(err, fallback = 'Something went wrong. Please try again.') {
  if (err?.code === 'ECONNABORTED' || err?.code === 'ETIMEDOUT') {
    return 'This is taking longer than expected. The server may still be waking up. Please try again in a few seconds.'
  }
  if (!err?.response) {
    return err?.request
      ? "Can't reach the server. Check your internet connection and try again."
      : fallback
  }
  const { status, data } = err.response
  if (status === 429) return 'Too many requests. Please wait a minute and try again.'
  if (status >= 500) return 'The server is busy or had a problem. Please try again in a moment.'
  const detail = data?.detail
  if (typeof detail === 'string' && detail) return detail
  if (status === 401) return 'Your session expired. Please sign in again.'
  if (status === 413) return 'That file is too large. Try a smaller resume.'
  if (status === 422)
    return 'Some of your input is invalid or too long. Please check it and try again.'
  return fallback
}
