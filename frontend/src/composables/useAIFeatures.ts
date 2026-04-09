import { ref, type Ref } from 'vue'

export interface SubtitleSegment {
  start: number
  end: number
  text: string
}

export interface SubtitleData {
  subtitles: SubtitleSegment[]
  language: string
  full_text: string
  is_auto: boolean
  is_danmaku?: boolean
  available_langs: string[]
  error?: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

const subtitleData: Ref<SubtitleData | null> = ref(null)
const isLoadingSubtitle = ref(false)
const subtitleError = ref('')

const summaryContent = ref('')
const isLoadingSummary = ref(false)

const mindmapMarkdown = ref('')
const isLoadingMindmap = ref(false)

const chatMessages: Ref<ChatMessage[]> = ref([])
const isLoadingChat = ref(false)

const currentVideoUrl = ref('')
const currentVideoTitle = ref('')

function resetAll() {
  subtitleData.value = null
  isLoadingSubtitle.value = false
  subtitleError.value = ''
  summaryContent.value = ''
  isLoadingSummary.value = false
  mindmapMarkdown.value = ''
  isLoadingMindmap.value = false
  chatMessages.value = []
  isLoadingChat.value = false
  currentVideoUrl.value = ''
  currentVideoTitle.value = ''
}

function setVideo(url: string, title: string) {
  if (url !== currentVideoUrl.value) {
    resetAll()
    currentVideoUrl.value = url
    currentVideoTitle.value = title
  }
}

async function fetchSubtitle(): Promise<SubtitleData | null> {
  if (subtitleData.value) return subtitleData.value
  if (!currentVideoUrl.value) return null

  isLoadingSubtitle.value = true
  subtitleError.value = ''

  try {
    const res = await fetch('/api/subtitle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: currentVideoUrl.value }),
    })
    const data = await res.json()
    if (!res.ok) {
      subtitleError.value = data.detail || '字幕提取失败'
      return null
    }
    if (data.error) {
      subtitleError.value = data.error
      return null
    }
    subtitleData.value = data
    return data
  } catch {
    subtitleError.value = '网络错误，请稍后重试'
    return null
  } finally {
    isLoadingSubtitle.value = false
  }
}

async function ensureSubtitle(): Promise<boolean> {
  if (subtitleData.value?.full_text) return true
  const data = await fetchSubtitle()
  return !!data?.full_text
}

function readSSEStream(
  response: Response,
  onToken: (token: string) => void,
  onDone: () => void,
  onError: (err: string) => void,
) {
  const reader = response.body?.getReader()
  if (!reader) {
    onError('无法读取响应流')
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''

  function processLines(text: string) {
    buffer += text
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6))
          if (data.done) {
            onDone()
            return
          }
          if (data.token) {
            onToken(data.token)
          }
          if (data.error) {
            onError(data.error)
            return
          }
        } catch { /* skip malformed lines */ }
      }
    }
  }

  ;(async function pump() {
    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          if (buffer) processLines('\n')
          onDone()
          break
        }
        processLines(decoder.decode(value, { stream: true }))
      }
    } catch {
      onError('连接中断')
    }
  })()
}

async function generateSummary() {
  if (isLoadingSummary.value) return
  if (!(await ensureSubtitle())) return

  isLoadingSummary.value = true
  summaryContent.value = ''

  try {
    const res = await fetch('/api/summary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: currentVideoUrl.value,
        title: currentVideoTitle.value,
      }),
    })

    if (!res.ok) {
      const err = await res.json()
      summaryContent.value = `错误：${err.detail || '生成失败'}`
      isLoadingSummary.value = false
      return
    }

    readSSEStream(
      res,
      (token) => { summaryContent.value += token },
      () => { isLoadingSummary.value = false },
      (err) => {
        summaryContent.value += `\n\n错误：${err}`
        isLoadingSummary.value = false
      },
    )
  } catch {
    summaryContent.value = '网络错误，请稍后重试'
    isLoadingSummary.value = false
  }
}

async function sendChatMessage(content: string) {
  if (isLoadingChat.value || !content.trim()) return
  if (!(await ensureSubtitle())) return

  chatMessages.value.push({ role: 'user', content: content.trim() })
  chatMessages.value.push({ role: 'assistant', content: '' })
  isLoadingChat.value = true

  const assistantIdx = chatMessages.value.length - 1
  const apiMessages = chatMessages.value
    .slice(0, -1)
    .map(m => ({ role: m.role, content: m.content }))

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: currentVideoUrl.value,
        title: currentVideoTitle.value,
        messages: apiMessages,
      }),
    })

    if (!res.ok) {
      const err = await res.json()
      chatMessages.value[assistantIdx].content = `错误：${err.detail || '回答失败'}`
      isLoadingChat.value = false
      return
    }

    readSSEStream(
      res,
      (token) => { chatMessages.value[assistantIdx].content += token },
      () => { isLoadingChat.value = false },
      (err) => {
        chatMessages.value[assistantIdx].content += `\n\n错误：${err}`
        isLoadingChat.value = false
      },
    )
  } catch {
    chatMessages.value[assistantIdx].content = '网络错误，请稍后重试'
    isLoadingChat.value = false
  }
}

async function generateMindmap() {
  if (isLoadingMindmap.value) return
  if (!(await ensureSubtitle())) return

  isLoadingMindmap.value = true
  mindmapMarkdown.value = ''

  try {
    const res = await fetch('/api/mindmap', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: currentVideoUrl.value,
        title: currentVideoTitle.value,
      }),
    })

    if (!res.ok) {
      const err = await res.json()
      mindmapMarkdown.value = `错误：${err.detail || '生成失败'}`
      isLoadingMindmap.value = false
      return
    }

    readSSEStream(
      res,
      (token) => { mindmapMarkdown.value += token },
      () => { isLoadingMindmap.value = false },
      (err) => {
        mindmapMarkdown.value += `\n\n错误：${err}`
        isLoadingMindmap.value = false
      },
    )
  } catch {
    mindmapMarkdown.value = '网络错误，请稍后重试'
    isLoadingMindmap.value = false
  }
}

export function useAIFeatures() {
  return {
    subtitleData,
    isLoadingSubtitle,
    subtitleError,
    summaryContent,
    isLoadingSummary,
    mindmapMarkdown,
    isLoadingMindmap,
    chatMessages,
    isLoadingChat,
    currentVideoUrl,
    currentVideoTitle,
    setVideo,
    resetAll,
    fetchSubtitle,
    ensureSubtitle,
    generateSummary,
    sendChatMessage,
    generateMindmap,
  }
}
