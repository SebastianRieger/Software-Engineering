import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import News from '@/components/widgets/News.vue'

const makeNewsItem = (overrides: Partial<Record<string, unknown>> = {}) => ({
  sophoraId: 'id-1',
  title: 'Test Headline',
  topline: 'Topline',
  firstSentence: 'First sentence.',
  date: new Date().toISOString(),
  shareURL: 'https://example.com',
  detailsweb: 'https://example.com',
  ressort: 'inland',
  breakingNews: false,
  teaserImage: {
    imageVariants: { '16x9-960': 'https://example.com/img.jpg' },
    alttext: 'Alt text',
  },
  ...overrides,
})

const mockFetch = (items: unknown[] = [makeNewsItem()]) => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ news: items }),
    })
  )
}

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('News widget', () => {
  it('shows loading state while fetching', () => {
    // Fetch never resolves → loading stays true
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise(() => {})))
    const wrapper = mount(News)
    expect(wrapper.text()).toContain('Lädt')
  })

  it('displays news items after successful fetch', async () => {
    mockFetch([makeNewsItem({ title: 'Breaking News' })])
    const wrapper = mount(News)
    await flushPromises()

    expect(wrapper.text()).toContain('Breaking News')
    expect(wrapper.text()).not.toContain('Lädt')
  })

  it('shows error state when fetch fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 500 })
    )
    const wrapper = mount(News)
    await flushPromises()

    expect(wrapper.text()).toContain('Nachrichten nicht verfügbar')
  })

  it('shows "Keine Meldungen" when news array is empty', async () => {
    mockFetch([])
    const wrapper = mount(News)
    await flushPromises()

    expect(wrapper.text()).toContain('Keine Meldungen')
  })

  it('renders tagesschau logo in the header', async () => {
    mockFetch()
    const wrapper = mount(News)
    await flushPromises()

    expect(wrapper.text()).toContain('tagesschau')
  })

  it('renders in medium size when cellSizes provides value 2', async () => {
    mockFetch([
      makeNewsItem({ title: 'News 1' }),
      makeNewsItem({ sophoraId: 'id-2', title: 'News 2' }),
      makeNewsItem({ sophoraId: 'id-3', title: 'News 3' }),
      makeNewsItem({ sophoraId: 'id-4', title: 'News 4' }),
    ])

    const wrapper = mount(News, {
      global: {
        provide: {
          cellId: 1,
          cellSizes: ref({ 1: 2 }),
        },
      },
    })
    await flushPromises()

    expect(wrapper.find('.ts-rows').exists()).toBe(true)
  })

  it('renders in large size when cellSizes provides value 4', async () => {
    mockFetch([
      makeNewsItem({ title: 'News 1' }),
      makeNewsItem({ sophoraId: 'id-2', title: 'News 2' }),
    ])

    const wrapper = mount(News, {
      global: {
        provide: {
          cellId: 2,
          cellSizes: ref({ 2: 4 }),
        },
      },
    })
    await flushPromises()

    expect(wrapper.find('.ts-large-grid').exists()).toBe(true)
  })

  it('renders in small size by default (no provide)', async () => {
    mockFetch([makeNewsItem(), makeNewsItem({ sophoraId: 'id-2', title: 'Second' })])
    const wrapper = mount(News)
    await flushPromises()

    expect(wrapper.find('.ts-list').exists()).toBe(true)
  })

  it('shows image placeholder when item has no teaserImage', async () => {
    mockFetch([
      makeNewsItem({ teaserImage: undefined }),
      makeNewsItem({ sophoraId: 'id-2', teaserImage: undefined }),
    ])

    const wrapper = mount(News, {
      global: {
        provide: { cellId: 3, cellSizes: ref({ 3: 4 }) },
      },
    })
    await flushPromises()

    expect(wrapper.find('.ts-image-placeholder').exists()).toBe(true)
  })

  it('renders breaking news styling', async () => {
    mockFetch([makeNewsItem({ breakingNews: true })])
    const wrapper = mount(News)
    await flushPromises()

    expect(wrapper.find('.ts-item--breaking').exists()).toBe(true)
  })

  it('shows topline text when present', async () => {
    mockFetch([makeNewsItem({ topline: 'Eilmeldung Topline' })])
    const wrapper = mount(News)
    await flushPromises()

    expect(wrapper.text()).toContain('Eilmeldung Topline')
  })

  it('clears the refresh interval on unmount', async () => {
    mockFetch()
    const clearSpy = vi.spyOn(window, 'clearInterval')
    const wrapper = mount(News)
    await flushPromises()
    wrapper.unmount()
    expect(clearSpy).toHaveBeenCalled()
  })

  it('handles fetch error thrown as a non-Error value', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue('string error')
    )
    const wrapper = mount(News)
    await flushPromises()

    expect(wrapper.text()).toContain('Nachrichten nicht verfügbar')
  })

  // ── Medium-size branch coverage ─────────────────────────────────────────

  it('renders breaking news row styling in medium size', async () => {
    mockFetch([
      makeNewsItem({ breakingNews: true }),
      makeNewsItem({ sophoraId: 'id-2', breakingNews: true }),
    ])
    const wrapper = mount(News, {
      global: { provide: { cellId: 10, cellSizes: ref({ 10: 2 }) } },
    })
    await flushPromises()

    expect(wrapper.find('.ts-row--breaking').exists()).toBe(true)
  })

  it('shows topline as badge in medium size when ressort is absent', async () => {
    mockFetch([
      makeNewsItem({ ressort: undefined, topline: 'Politik' }),
      makeNewsItem({ sophoraId: 'id-2', ressort: undefined, topline: 'Sport' }),
    ])
    const wrapper = mount(News, {
      global: { provide: { cellId: 10, cellSizes: ref({ 10: 2 }) } },
    })
    await flushPromises()

    const badges = wrapper.findAll('.ts-badge')
    expect(badges[0]!.text()).toBe('Politik')
  })

  it('shows em dash as badge in medium size when both ressort and topline are absent', async () => {
    mockFetch([
      makeNewsItem({ ressort: undefined, topline: undefined }),
      makeNewsItem({ sophoraId: 'id-2', ressort: undefined, topline: undefined }),
    ])
    const wrapper = mount(News, {
      global: { provide: { cellId: 10, cellSizes: ref({ 10: 2 }) } },
    })
    await flushPromises()

    const badge = wrapper.find('.ts-badge')
    expect(badge.text()).toBe('—')
  })

  // ── Large-size branch coverage ──────────────────────────────────────────

  it('renders breaking news badge and card styling in large size', async () => {
    mockFetch([
      makeNewsItem({ breakingNews: true }),
      makeNewsItem({ sophoraId: 'id-2', breakingNews: true }),
    ])
    const wrapper = mount(News, {
      global: { provide: { cellId: 11, cellSizes: ref({ 11: 4 }) } },
    })
    await flushPromises()

    expect(wrapper.find('.ts-breaking-badge').exists()).toBe(true)
    expect(wrapper.find('.ts-large-card--breaking').exists()).toBe(true)
  })

  it('renders large size gracefully without optional fields (topline / firstSentence / ressort / date)', async () => {
    mockFetch([
      makeNewsItem({ topline: undefined, firstSentence: undefined, ressort: undefined, date: '' }),
      makeNewsItem({ sophoraId: 'id-2', topline: undefined, firstSentence: undefined, ressort: undefined, date: '' }),
    ])
    const wrapper = mount(News, {
      global: { provide: { cellId: 11, cellSizes: ref({ 11: 4 }) } },
    })
    await flushPromises()

    expect(wrapper.find('.ts-large-grid').exists()).toBe(true)
    // Optional elements must not render when their data is absent
    expect(wrapper.find('.ts-teaser--large').exists()).toBe(false)
    expect(wrapper.find('.ts-ressort').exists()).toBe(false)
    expect(wrapper.find('.ts-time').exists()).toBe(false)
  })

  // ── getImage() fallback chains ──────────────────────────────────────────

  it('uses 16x9-640 variant when 16x9-960 is absent', async () => {
    mockFetch([
      makeNewsItem({ teaserImage: { imageVariants: { '16x9-640': 'https://img.example.com/640.jpg' }, alttext: 'Alt' } }),
      makeNewsItem({ sophoraId: 'id-2', teaserImage: { imageVariants: { '16x9-640': 'https://img.example.com/640-b.jpg' }, alttext: 'B' } }),
    ])
    const wrapper = mount(News, {
      global: { provide: { cellId: 12, cellSizes: ref({ 12: 4 }) } },
    })
    await flushPromises()

    const img = wrapper.find('.ts-image')
    expect(img.exists()).toBe(true)
    expect(img.attributes('src')).toBe('https://img.example.com/640.jpg')
  })

  it('uses 16x9-480 variant as third fallback', async () => {
    mockFetch([
      makeNewsItem({ teaserImage: { imageVariants: { '16x9-480': 'https://img.example.com/480.jpg' }, alttext: 'Alt' } }),
      makeNewsItem({ sophoraId: 'id-2', teaserImage: { imageVariants: { '16x9-480': 'https://img.example.com/480-b.jpg' }, alttext: 'B' } }),
    ])
    const wrapper = mount(News, {
      global: { provide: { cellId: 12, cellSizes: ref({ 12: 4 }) } },
    })
    await flushPromises()

    const img = wrapper.find('.ts-image')
    expect(img.exists()).toBe(true)
    expect(img.attributes('src')).toBe('https://img.example.com/480.jpg')
  })

  it('uses first available variant key as last-resort fallback', async () => {
    mockFetch([
      makeNewsItem({ teaserImage: { imageVariants: { 'custom-key': 'https://img.example.com/custom.jpg' }, alttext: 'Alt' } }),
      makeNewsItem({ sophoraId: 'id-2', teaserImage: { imageVariants: { 'custom-key': 'https://img.example.com/custom-b.jpg' }, alttext: 'B' } }),
    ])
    const wrapper = mount(News, {
      global: { provide: { cellId: 12, cellSizes: ref({ 12: 4 }) } },
    })
    await flushPromises()

    const img = wrapper.find('.ts-image')
    expect(img.exists()).toBe(true)
    expect(img.attributes('src')).toBe('https://img.example.com/custom.jpg')
  })
})
