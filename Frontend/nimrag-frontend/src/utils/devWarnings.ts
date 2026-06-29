const warnedMessages = new Set<string>()

export function warnDevOnce(scope: string, message: string, error?: unknown): void {
  if (!import.meta.env.DEV) {
    return
  }

  const key = `${scope}:${message}`
  if (warnedMessages.has(key)) {
    return
  }

  warnedMessages.add(key)
  if (error === undefined) {
    console.warn(`[${scope}] ${message}`)
    return
  }

  console.warn(`[${scope}] ${message}`, error)
}
