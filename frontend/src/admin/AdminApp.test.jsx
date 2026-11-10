import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./adminApi', () => ({
  adminApi: new Proxy({}, { get: () => vi.fn().mockResolvedValue([]) }),
  errMsg: (e) => e.message,
}))

import AdminApp from './AdminApp'

beforeEach(() => {
  window.location.hash = ''
})

describe('AdminApp', () => {
  it('shows the overview by default and marks it current', async () => {
    window.location.hash = '#/admin'
    render(<AdminApp />)
    expect(await screen.findByRole('heading', { name: 'Overview' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /overview/i, current: 'page' })).toBeInTheDocument()
  })

  it('routes to the audit log from the hash', async () => {
    window.location.hash = '#/admin/audit'
    render(<AdminApp />)
    expect(await screen.findByRole('heading', { name: 'Audit log' })).toBeInTheDocument()
  })

  it('falls back to the overview for an unknown page', async () => {
    window.location.hash = '#/admin/nope'
    render(<AdminApp />)
    expect(await screen.findByRole('heading', { name: 'Overview' })).toBeInTheDocument()
  })
})
