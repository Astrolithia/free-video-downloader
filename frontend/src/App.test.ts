import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockState = vi.hoisted(() => ({
  videoInfoValue: {
    title: '测试视频',
    thumbnail: '/thumb.jpg',
    duration: 95,
    uploader: 'tester',
    webpage_url: 'https://www.bilibili.com/video/BV1XVDfBLE3D',
    extractor: 'generic',
    stream_format_id: '30016',
    formats: [
      {
        format_id: '30016',
        label: '360p',
        ext: 'mp4',
        filesize: 123,
        best_audio_id: '30280',
      },
    ],
  },
  videoInfoRef: null as any,
  isParsingRef: null as any,
  parseErrorRef: null as any,
  progressRef: null as any,
  parseVideo: vi.fn(),
  debouncedParse: vi.fn(),
  progressValue: {
    status: 'idle' as 'idle' | 'downloading' | 'merging' | 'done' | 'error',
    percent: 0,
    speed: '',
    eta: '',
    error: '',
    taskId: '',
  },
  startDownload: vi.fn(),
  setVideo: vi.fn(),
}))

vi.mock('./components/NavBar.vue', () => ({
  default: { template: '<div />' },
}))

vi.mock('./components/HeroSection.vue', () => ({
  default: { template: '<div />' },
}))

vi.mock('./components/DownloadProgress.vue', () => ({
  default: { template: '<div />' },
}))

vi.mock('./components/AIPanel.vue', () => ({
  default: { template: '<div />' },
}))

vi.mock('./components/FeatureGrid.vue', () => ({
  default: { template: '<div />' },
}))

vi.mock('./components/PlatformList.vue', () => ({
  default: { template: '<div />' },
}))

vi.mock('./components/VideoResult.vue', async () => {
  const { defineComponent, h } = await import('vue')

  return {
    default: defineComponent({
      name: 'VideoResult',
      props: {
        info: { type: Object, required: true },
        playerSrc: { type: String, default: '' },
      },
      emits: ['download'],
      setup(props, { emit }) {
        return () =>
          h('div', { 'data-testid': 'video-result', 'data-player-src': props.playerSrc }, [
            h(
              'button',
              {
                class: 'download-trigger',
                onClick: () => emit('download', props.info.webpage_url, '30016', '30280'),
              },
              'download',
            ),
          ])
      },
    }),
  }
})

vi.mock('./composables/useVideoParser', async () => {
  const { ref } = await import('vue')

  mockState.videoInfoRef ||= ref(mockState.videoInfoValue)
  mockState.isParsingRef ||= ref(false)
  mockState.parseErrorRef ||= ref('')

  return {
    useVideoParser: () => ({
      videoInfo: mockState.videoInfoRef,
      isParsing: mockState.isParsingRef,
      parseError: mockState.parseErrorRef,
      parseVideo: mockState.parseVideo,
      debouncedParse: mockState.debouncedParse,
    }),
  }
})

vi.mock('./composables/useDownloader', async () => {
  const { reactive } = await import('vue')

  mockState.progressRef ||= reactive({ ...mockState.progressValue })

  return {
    useDownloader: () => ({
      progress: mockState.progressRef,
      startDownload: mockState.startDownload,
    }),
  }
})

vi.mock('./composables/useAIFeatures', () => ({
  useAIFeatures: () => ({
    setVideo: mockState.setVideo,
  }),
}))

import App from './App.vue'

describe('App download playback flow', () => {
  beforeEach(() => {
    mockState.videoInfoRef.value = { ...mockState.videoInfoValue }
    mockState.progressRef.status = 'idle'
    mockState.progressRef.percent = 0
    mockState.progressRef.speed = ''
    mockState.progressRef.eta = ''
    mockState.progressRef.error = ''
    mockState.progressRef.taskId = ''
    mockState.startDownload.mockReset()
    mockState.setVideo.mockReset()
  })

  it('keeps the cover visible while the download is still running', async () => {
    const wrapper = mount(App)

    expect(wrapper.get('[data-testid="video-result"]').attributes('data-player-src')).toBe('')

    await wrapper.get('.download-trigger').trigger('click')

    expect(mockState.startDownload).toHaveBeenCalledWith(
      'https://www.bilibili.com/video/BV1XVDfBLE3D',
      '30016',
      '30280',
    )
    expect(wrapper.get('[data-testid="video-result"]').attributes('data-player-src')).toBe('')
  })

  it('switches to the downloaded file for inline playback once the task is done', async () => {
    const wrapper = mount(App)

    await wrapper.get('.download-trigger').trigger('click')
    mockState.progressRef.status = 'done'
    mockState.progressRef.taskId = 'task-123'
    await wrapper.vm.$nextTick()

    expect(wrapper.get('[data-testid="video-result"]').attributes('data-player-src')).toBe('/api/play/task-123')
  })

  it('still switches to the downloaded file when the parsed metadata has no preview format id', async () => {
    mockState.videoInfoRef.value = {
      ...mockState.videoInfoValue,
      stream_format_id: null,
    }

    const wrapper = mount(App)

    await wrapper.get('.download-trigger').trigger('click')
    mockState.progressRef.status = 'done'
    mockState.progressRef.taskId = 'task-456'
    await wrapper.vm.$nextTick()

    expect(wrapper.get('[data-testid="video-result"]').attributes('data-player-src')).toBe('/api/play/task-456')
  })
})
