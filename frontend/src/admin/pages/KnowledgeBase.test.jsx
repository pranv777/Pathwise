import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../adminApi', () => ({
  adminApi: { kb: vi.fn(), kbUpload: vi.fn(), kbDelete: vi.fn(), kbReseed: vi.fn() },
  errMsg: (e) => e.message,
}))

import { adminApi } from '../adminApi'
import KnowledgeBase from './KnowledgeBase'

const kb = {
  documents: 1,
  chunks: 3,
  items: [{ source: 'guide.txt', doc_type: 'career_guide', chunks: 3 }],
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(adminApi.kb).mockResolvedValue(kb)
  vi.mocked(adminApi.kbUpload).mockResolvedValue({ data: {} })
  vi.mocked(adminApi.kbDelete).mockResolvedValue(/** @type {any} */ ({}))
  vi.mocked(adminApi.kbReseed).mockResolvedValue({ data: {} })
})
afterEach(() => vi.restoreAllMocks())

describe('KnowledgeBase page', () => {
  it('shows totals and documents', async () => {
    render(<KnowledgeBase />)
    expect(await screen.findByText('guide.txt')).toBeInTheDocument()
    expect(screen.getByText('Documents')).toBeInTheDocument()
    expect(screen.getByText('3', { selector: 'div' })).toBeInTheDocument()
  })

  it('shows an empty state and load errors', async () => {
    vi.mocked(adminApi.kb).mockResolvedValue({ documents: 0, chunks: 0, items: [] })
    const { unmount } = render(<KnowledgeBase />)
    expect(await screen.findByText('No shared documents indexed.')).toBeInTheDocument()
    unmount()
    vi.mocked(adminApi.kb).mockRejectedValue(new Error('down'))
    render(<KnowledgeBase />)
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })

  it('asks for a file before uploading', async () => {
    const user = userEvent.setup()
    render(<KnowledgeBase />)
    await screen.findByText('guide.txt')
    await user.click(screen.getByRole('button', { name: 'Upload' }))
    expect(screen.getByRole('status')).toHaveTextContent(
      'Choose a PDF, DOCX, TXT or MD file first.',
    )
    expect(adminApi.kbUpload).not.toHaveBeenCalled()
  })

  it('uploads the chosen file with the chosen type and reloads', async () => {
    const user = userEvent.setup()
    const { container } = render(<KnowledgeBase />)
    await screen.findByText('guide.txt')
    await user.selectOptions(screen.getByLabelText('Type'), 'interview_prep')
    const file = new File(['hi'], 'notes.md', { type: 'text/markdown' })
    await user.upload(container.querySelector('input[type="file"]'), file)
    await user.click(screen.getByRole('button', { name: 'Upload' }))
    await waitFor(() => expect(adminApi.kbUpload).toHaveBeenCalledWith('interview_prep', file))
    expect(await screen.findByText(/Indexed notes\.md/)).toBeInTheDocument()
    expect(adminApi.kb).toHaveBeenCalledTimes(2)
  })

  it('reports upload failures', async () => {
    vi.mocked(adminApi.kbUpload).mockRejectedValue(new Error('too big'))
    const user = userEvent.setup()
    const { container } = render(<KnowledgeBase />)
    await screen.findByText('guide.txt')
    await user.upload(container.querySelector('input[type="file"]'), new File(['x'], 'a.txt'))
    await user.click(screen.getByRole('button', { name: 'Upload' }))
    expect(await screen.findByText('too big')).toBeInTheDocument()
  })

  it('deletes a document after confirmation only', async () => {
    const user = userEvent.setup()
    const confirm = vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValue(true)
    render(<KnowledgeBase />)
    await user.click(await screen.findByRole('button', { name: 'Delete' }))
    expect(adminApi.kbDelete).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Delete' }))
    await waitFor(() => expect(adminApi.kbDelete).toHaveBeenCalledWith('guide.txt'))
    expect(confirm).toHaveBeenCalledTimes(2)
    expect(await screen.findByText('Deleted guide.txt.')).toBeInTheDocument()
  })

  it('re-seeds after confirmation only', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValue(true)
    render(<KnowledgeBase />)
    await screen.findByText('guide.txt')
    await user.click(screen.getByRole('button', { name: 'Re-seed' }))
    expect(adminApi.kbReseed).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Re-seed' }))
    await waitFor(() => expect(adminApi.kbReseed).toHaveBeenCalled())
    expect(await screen.findByText('Seed ingestion finished.')).toBeInTheDocument()
  })
})
