import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockState = vi.hoisted(() => ({
  fetchSubtitle: vi.fn(),
  subtitleData: {
    subtitles: [
      { start: 14.61, end: 16.25, text: '♪ 呵哒哒哒 ♪' },
      { start: 18.18, end: 19.82, text: '♪ 哒 ♪' },
    ],
    language: 'ai-zh',
    full_text: '♪ 呵哒哒哒 ♪\n♪ 哒 ♪',
    is_auto: true,
    available_langs: ['ai-zh'],
  },
}))

vi.mock('@/composables/useAIFeatures', async () => {
  const { ref } = await import('vue')

  return {
    useAIFeatures: () => ({
      subtitleData: ref(mockState.subtitleData),
      isLoadingSubtitle: ref(false),
      subtitleError: ref(''),
      fetchSubtitle: mockState.fetchSubtitle,
    }),
  }
})

import SubtitleView from './SubtitleView.vue'
import { useVideoPlayer } from '@/composables/useVideoPlayer'

describe('SubtitleView', () => {
  beforeEach(() => {
    mockState.fetchSubtitle.mockReset()
    const player = useVideoPlayer()
    player.seekTime.value = 0
    player.seekCounter.value = 0
  })

  it('updates the shared player seek state when a timestamp is clicked', async () => {
    const wrapper = mount(SubtitleView)

    await wrapper.get('.subtitle-time').trigger('click')

    const player = useVideoPlayer()
    expect(player.seekTime.value).toBe(14.61)
    expect(player.seekCounter.value).toBe(1)
  })
})
