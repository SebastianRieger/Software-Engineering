import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { warnDevOnce } from '@/utils/devWarnings'

describe('warnDevOnce', () => {
  let warnSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
  })

  afterEach(() => {
    warnSpy.mockRestore()
  })

  it('does nothing when not in DEV mode', () => {
    const originalDev = import.meta.env.DEV
    import.meta.env.DEV = false
    try {
      warnDevOnce('scope-dev-off', 'should not log')
      expect(warnSpy).not.toHaveBeenCalled()
    } finally {
      import.meta.env.DEV = originalDev
    }
  })

  it('logs once with [scope] message when no error is given', () => {
    warnDevOnce('scope-no-error', 'something went wrong')
    expect(warnSpy).toHaveBeenCalledOnce()
    expect(warnSpy).toHaveBeenCalledWith('[scope-no-error] something went wrong')
  })

  it('logs with the error object when an error is given', () => {
    const err = new Error('original cause')
    warnDevOnce('scope-with-error', 'something failed', err)
    expect(warnSpy).toHaveBeenCalledOnce()
    expect(warnSpy).toHaveBeenCalledWith('[scope-with-error] something failed', err)
  })

  it('suppresses duplicate warnings for the same scope and message', () => {
    warnDevOnce('scope-dedup', 'repeated message')
    warnDevOnce('scope-dedup', 'repeated message')
    expect(warnSpy).toHaveBeenCalledOnce()
  })
})
