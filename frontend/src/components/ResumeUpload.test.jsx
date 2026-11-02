import { render, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import ResumeUpload from './ResumeUpload.jsx'

function setup(overrides = {}) {
  const props = {
    profile: null,
    onUploaded: vi.fn().mockResolvedValue(undefined),
    onError: vi.fn(),
    onProfileChange: vi.fn(),
    loading: false,
    setLoading: vi.fn(),
    ...overrides,
  }
  const { container } = render(<ResumeUpload {...props} />)
  const input = /** @type {HTMLInputElement} */ (container.querySelector('input[type="file"]'))
  return { props, input }
}

describe('ResumeUpload', () => {
  it('rejects unsupported file types', async () => {
    // applyAccept:false so user-event doesn't silently drop the file before our check
    const user = userEvent.setup({ applyAccept: false })
    const { props, input } = setup()
    await user.upload(input, new File(['x'], 'photo.png', { type: 'image/png' }))
    expect(props.onError).toHaveBeenCalledWith(expect.stringMatching(/PDF/))
    expect(props.onUploaded).not.toHaveBeenCalled()
  })

  it('passes a valid file through and toggles loading', async () => {
    const user = userEvent.setup()
    const { props, input } = setup()
    const file = new File(['%PDF-1.4'], 'cv.pdf', { type: 'application/pdf' })
    await user.upload(input, file)
    await waitFor(() => expect(props.setLoading).toHaveBeenLastCalledWith(false))
    expect(props.onUploaded).toHaveBeenCalledWith(file)
    expect(props.setLoading).toHaveBeenNthCalledWith(1, true)
  })

  it('surfaces the backend error detail', async () => {
    const user = userEvent.setup()
    const { props, input } = setup({
      onUploaded: vi.fn().mockRejectedValue({ response: { data: { detail: 'Too big' } } }),
    })
    await user.upload(input, new File(['x'], 'cv.pdf', { type: 'application/pdf' }))
    await waitFor(() => expect(props.onError).toHaveBeenCalledWith('Too big'))
  })
})
