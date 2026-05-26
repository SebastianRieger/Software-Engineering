import { buildApiUrl } from './apiConfig'

export class ApiError extends Error {
  status: number
  details: unknown

  constructor(message: string, status: number, details: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
  }
}

function hasJsonBody(body: BodyInit | null | undefined): body is Exclude<BodyInit, FormData> {
  return body !== undefined && body !== null && !(body instanceof FormData)
}

async function parseResponseBody(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return null
  }

  const contentType = response.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    return response.json()
  }

  return response.text()
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json')
  }
  if (hasJsonBody(init.body) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(buildApiUrl(path), {
    ...init,
    headers,
  })

  const payload = await parseResponseBody(response)
  if (!response.ok) {
    const message = typeof payload === 'string' && payload.length > 0
      ? payload
      : response.statusText || 'Request failed'
    throw new ApiError(message, response.status, payload)
  }

  return payload as T
}

export function getJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  return apiRequest<T>(path, { ...init, method: init.method ?? 'GET' })
}

export function sendJson<TResponse>(
  path: string,
  method: 'POST' | 'PUT' | 'PATCH' | 'DELETE',
  body?: unknown,
  init: RequestInit = {},
): Promise<TResponse> {
  return apiRequest<TResponse>(path, {
    ...init,
    method,
    body: body === undefined ? init.body : JSON.stringify(body),
  })
}