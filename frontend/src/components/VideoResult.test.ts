import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import VideoResult from './VideoResult.vue'

const info = {
  title: '测试视频',
  thumbnail: '/thumb.jpg',
  duration: 95,
  uploader: 'tester',
  webpage_url: 'https://example.com/video',
  extractor: 'generic',
  stream_format_id: '18',
  formats: [
    {
      format_id: '18',
      label: '360p',
      ext: 'mp4',
      filesize: 123,
      best_audio_id: null,
    },
  ],
}

describe('VideoResult', () => {
  it('shows the cover image before a player source is provided', () => {
    const wrapper = mount(VideoResult, {
      props: { info },
    })

    expect(wrapper.find('img').exists()).toBe(true)
    expect(wrapper.find('video').exists()).toBe(false)
  })

  it('replaces the cover image with the player when playerSrc is provided', () => {
    const wrapper = mount(VideoResult, {
      props: {
        info,
        playerSrc: '/api/play/task-id',
      },
    })

    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.find('video').exists()).toBe(true)
  })
})
