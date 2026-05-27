import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, apiRequest, getJson, sendJson } from '@/services/api'

const fetchMock = vi.fn()

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('api service', () => {
  it('uses GET by default and parses JSON responses', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await expect(getJson<{ ok: boolean }>('/status')).resolves.toEqual({ ok: true })

    expect(fetchMock).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/status',
      expect.objectContaining({ method: 'GET', headers: expect.any(Headers) }),
    )

    const requestInit = fetchMock.mock.calls[0][1] as RequestInit
    const headers = requestInit.headers as Headers
    expect(headers.get('Accept')).toBe('application/json')
    expect(headers.get('Content-Type')).toBeNull()
  })

  it('serializes JSON payloads and sets the content type automatically', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ created: true }), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await expect(sendJson('/widgets', 'POST', { id: 7 })).resolves.toEqual({ created: true })

    const requestInit = fetchMock.mock.calls[0][1] as RequestInit
    const headers = requestInit.headers as Headers
    expect(requestInit.body).toBe('{"id":7}')
    expect(headers.get('Content-Type')).toBe('application/json')
  })

  it('keeps an existing request body when sendJson receives no body argument', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ accepted: true }), {
        status: 202,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await expect(
      sendJson('/widgets', 'PATCH', undefined, { body: 'keep-me' }),
    ).resolves.toEqual({ accepted: true })

    const requestInit = fetchMock.mock.calls[0][1] as RequestInit
    expect(requestInit.body).toBe('keep-me')
  })

  it('does not force JSON headers for form data payloads', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ uploaded: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const formData = new FormData()
    formData.set('file', 'payload')

    await expect(apiRequest('/upload', { method: 'POST', body: formData })).resolves.toEqual({ uploaded: true })

    const requestInit = fetchMock.mock.calls[0][1] as RequestInit
    const headers = requestInit.headers as Headers
    expect(headers.get('Content-Type')).toBeNull()
  })

  it('returns null for 204 responses', async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }))

    await expect(apiRequest<null>('/empty')).resolves.toBeNull()
  })

  it('throws ApiError with the response text when a request fails', async () => {
    fetchMock.mockResolvedValue(
      new Response('backend exploded', {
        status: 500,
        headers: { 'Content-Type': 'text/plain' },
      }),
    )

    let error: unknown
    try {
      await apiRequest('/boom')
    } catch (caught) {
      error = caught
    }

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({
      message: 'backend exploded',
      name: 'ApiError',
      status: 500,
      details: 'backend exploded',
    })
  })

  it('falls back to the HTTP status text when an error response body is empty', async () => {
    fetchMock.mockResolvedValue(
      new Response('', {
        status: 503,
        statusText: 'Service Unavailable',
        headers: { 'Content-Type': 'text/plain' },
      }),
    )

    await expect(apiRequest('/health')).rejects.toMatchObject({
      message: 'Service Unavailable',
      status: 503,
      details: '',
    })
  })
})