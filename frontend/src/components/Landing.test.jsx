import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import Landing from './Landing'

afterEach(() => vi.unstubAllGlobals())

function stubObserver() {
  const observers = []
  class FakeObserver {
    constructor(cb) {
      this.cb = cb
      this.disconnect = vi.fn()
      observers.push(this)
    }
    observe() {}
  }
  vi.stubGlobal('IntersectionObserver', FakeObserver)
  return observers
}

describe('Landing', () => {
  it('renders the page with sign-in links and the main sections', () => {
    const { container } = render(<Landing />)
    expect(screen.getAllByText('Pathwise').length).toBeGreaterThan(0)
    for (const id of ['features', 'how-it-works', 'about']) {
      expect(container.querySelector(`#${id}`)).toBeInTheDocument()
    }
    expect(container.querySelectorAll('a[href="#/signin"]').length).toBeGreaterThan(0)
  })

  it('opens and closes the mobile menu', async () => {
    const user = userEvent.setup()
    render(<Landing />)
    await user.click(screen.getByRole('button', { name: 'Open menu' }))
    expect(screen.getByRole('button', { name: 'Close menu' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
    await user.click(screen.getAllByRole('link', { name: 'Features' }).at(-1))
    expect(screen.getByRole('button', { name: 'Open menu' })).toBeInTheDocument()
  })

  it('adds a background to the navbar after scrolling', () => {
    render(<Landing />)
    const header = screen.getByRole('banner')
    expect(header.className).toContain('border-transparent')
    act(() => {
      Object.defineProperty(window, 'scrollY', { value: 100, configurable: true })
      window.dispatchEvent(new Event('scroll'))
    })
    expect(header.className).toContain('backdrop-blur')
    Object.defineProperty(window, 'scrollY', { value: 0, configurable: true })
  })

  it('reveals sections as they scroll into view', () => {
    const observers = stubObserver()
    const { container } = render(<Landing />)
    expect(container.querySelectorAll('.reveal--in')).toHaveLength(0)
    act(() => observers.forEach((o) => o.cb([{ isIntersecting: true }])))
    expect(container.querySelectorAll('.reveal--in').length).toBeGreaterThan(0)
    expect(observers[0].disconnect).toHaveBeenCalled()
  })

  it('ignores observer callbacks for elements that are not visible', () => {
    const observers = stubObserver()
    const { container } = render(<Landing />)
    act(() => observers.forEach((o) => o.cb([{ isIntersecting: false }])))
    expect(container.querySelectorAll('.reveal--in')).toHaveLength(0)
  })
})
