import { ref, type Ref } from 'vue'

export interface VideoFormat {
  format_id: string
  label: string
  ext: string
  filesize: number | null
  best_audio_id: string | null
}

export interface VideoInfo {
  title: string
  thumbnail: string
  duration: number | null
  uploader: string | null
  webpage_url: string
  extractor: string
  formats: VideoFormat[]
  stream_format_id: string | null
}

export function useVideoParser() {
  const videoInfo: Ref<VideoInfo | null> = ref(null)
  const isParsing = ref(false)
  const parseError = ref('')

  let debounceTimer: ReturnType<typeof setTimeout> | null = null

  async function parseVideo(url: string) {
    if (isParsing.value) return
    if (!url.trim()) {
      parseError.value = '请粘贴视频链接'
      return
    }

    parseError.value = ''
    videoInfo.value = null
    isParsing.value = true

    try {
      const res = await fetch('/api/parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      })

      const data = await res.json()
      if (!res.ok) {
        parseError.value = data.detail || '解析失败，请检查链接'
        return
      }

      parseError.value = ''
      videoInfo.value = data
    } catch {
      parseError.value = '网络错误，请稍后重试'
    } finally {
      isParsing.value = false
    }
  }

  function debouncedParse(url: string) {
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => parseVideo(url), 300)
  }

  return {
    videoInfo,
    isParsing,
    parseError,
    parseVideo,
    debouncedParse,
  }
}
