import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import CameraWidget from '@/components/widgets/CameraWidget.vue'

const stopTrack = vi.fn()
const makeStream = () => ({
  getTracks: () => [{ stop: stopTrack }],
}) as unknown as MediaStream

const makeCamera = (deviceId: string, label: string) => ({
  deviceId,
  label,
  kind: 'videoinput',
  groupId: '',
  toJSON: () => ({}),
}) as MediaDeviceInfo

const getUserMedia = vi.fn()
const enumerateDevices = vi.fn()

beforeEach(() => {
  localStorage.clear()
  stopTrack.mockReset()
  getUserMedia.mockReset()
  enumerateDevices.mockReset()
  getUserMedia.mockResolvedValue(makeStream())
  enumerateDevices.mockResolvedValue([
    makeCamera('camera-1', 'Built-in Camera'),
    makeCamera('camera-2', 'USB Camera'),
  ])
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: { getUserMedia, enumerateDevices },
  })
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue(undefined)
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('CameraWidget', () => {
  it('starts a camera preview on mount', async () => {
    mount(CameraWidget)
    await flushPromises()

    expect(getUserMedia).toHaveBeenCalledWith({ video: true, audio: false })
  })

  it('renders a dropdown when multiple cameras are available', async () => {
    const wrapper = mount(CameraWidget)
    await flushPromises()

    const options = wrapper.findAll('option')
    expect(wrapper.find('select').exists()).toBe(true)
    expect(options.map((option) => option.text())).toContain('USB Camera')
  })

  it('stops the stream on unmount', async () => {
    const wrapper = mount(CameraWidget)
    await flushPromises()

    wrapper.unmount()

    expect(stopTrack).toHaveBeenCalled()
  })
})