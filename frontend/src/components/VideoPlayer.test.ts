import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import VideoPlayer from './VideoPlayer.vue'
import { useVideoPlayer } from '@/composables/useVideoPlayer'

function stubVideoElement(video: HTMLVideoElement, initialReadyState: number, paused = true) {
  let currentTime = 0
  let readyState = initialReadyState

  const play = vi.fn().mockResolvedValue(undefined)
  const load = vi.fn()

  Object.defineProperty(video, 'currentTime', {
    configurable: true,
    get: () => currentTime,
    set: (value: number) => {
      currentTime = value
    },
  })

  Object.defineProperty(video, 'readyState', {
    configurable: true,
    get: () => readyState,
  })

  Object.defineProperty(video, 'paused', {
    configurable: true,
    get: () => paused,
  })

  Object.defineProperty(video, 'play', {
    configurable: true,
    value: play,
  })

  Object.defineProperty(video, 'load', {
    configurable: true,
    value: load,
  })

  return {
    play,
    load,
    getCurrentTime: () => currentTime,
    setReadyState: (value: number) => {
      readyState = value
    },
  }
}

describe('VideoPlayer', () => {
  beforeEach(() => {
    const player = useVideoPlayer()
    player.seekTime.value = 0
    player.seekCounter.value = 0
  })

  it('seeks immediately when metadata is already loaded', async () => {
    const wrapper = mount(VideoPlayer, {
      props: { src: '/preview.mp4' },
    })
    const video = wrapper.get('video').element as HTMLVideoElement
    const stub = stubVideoElement(video, 1)

    useVideoPlayer().seekTo(42.5)
    await nextTick()

    expect(stub.getCurrentTime()).toBe(42.5)
    expect(stub.play).not.toHaveBeenCalled()
  })

  it('waits for metadata before applying the seek', async () => {
    const wrapper = mount(VideoPlayer, {
      props: { src: '/preview.mp4' },
    })
    const video = wrapper.get('video').element as HTMLVideoElement
    const stub = stubVideoElement(video, 0)

    useVideoPlayer().seekTo(12)
    await nextTick()

    expect(stub.getCurrentTime()).toBe(0)

    stub.setReadyState(1)
    video.dispatchEvent(new Event('loadedmetadata'))
    await nextTick()

    expect(stub.getCurrentTime()).toBe(12)
    expect(stub.play).not.toHaveBeenCalled()
  })

  it('applies the latest seek after the player mounts', async () => {
    useVideoPlayer().seekTo(27)

    const wrapper = mount(VideoPlayer, {
      props: { src: '/preview.mp4' },
    })
    const video = wrapper.get('video').element as HTMLVideoElement
    const stub = stubVideoElement(video, 0)

    await nextTick()
    expect(stub.getCurrentTime()).toBe(0)

    stub.setReadyState(1)
    video.dispatchEvent(new Event('loadedmetadata'))
    await nextTick()

    expect(stub.getCurrentTime()).toBe(27)
    expect(stub.play).not.toHaveBeenCalled()
  })

  it('keeps playback going after a seek when the video is already playing', async () => {
    const wrapper = mount(VideoPlayer, {
      props: { src: '/preview.mp4' },
    })
    const video = wrapper.get('video').element as HTMLVideoElement
    const stub = stubVideoElement(video, 1, false)

    useVideoPlayer().seekTo(8)
    await nextTick()

    expect(stub.getCurrentTime()).toBe(8)
    expect(stub.play).toHaveBeenCalledTimes(1)
  })
})
