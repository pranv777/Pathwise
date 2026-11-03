import '@testing-library/jest-dom/vitest'
import { beforeEach, vi } from 'vitest'

// Node 22+ ships an experimental global localStorage that hides jsdom's.
// Replace it with a simple in-memory Storage so tests behave like a browser.
function memoryStorage() {
  let store = {}
  return {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => {
      store[k] = String(v)
    },
    removeItem: (k) => {
      delete store[k]
    },
    clear: () => {
      store = {}
    },
    key: (i) => Object.keys(store)[i] ?? null,
    get length() {
      return Object.keys(store).length
    },
  }
}

beforeEach(() => {
  vi.stubGlobal('localStorage', memoryStorage())
  vi.stubGlobal('sessionStorage', memoryStorage())
})
