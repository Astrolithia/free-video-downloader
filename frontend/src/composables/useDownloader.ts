import { reactive, onUnmounted } from 'vue'

export interface DownloadProgress {
  status: 'idle' | 'downloading' | 'merging' | 'done' | 'error'
  percent: number
  speed: string
  eta: string
  error: string
  taskId: string
}

export function useDownloader() {
  const progress = reactive<DownloadProgress>({
    status: 'idle',
    percent: 0,
    speed: '',
    eta: '',
    error: '',
    taskId: '',
  })

  let eventSource: EventSource | null = null

  function resetProgress() {
    progress.status = 'idle'
    progress.percent = 0
    progress.speed = ''
    progress.eta = ''
    progress.error = ''
    progress.taskId = ''
  }

  function closeEventSource() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
  }

  async function startDownload(url: string, formatId: string, audioId: string | null) {
    resetProgress()
    progress.status = 'downloading'

    try {
      const res = await fetch('/api/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url,
          format_id: formatId,
          audio_id: audioId || null,
        }),
      })

      const data = await res.json()
      if (!res.ok) {
        progress.status = 'error'
        progress.error = data.detail || '下载请求失败'
        return
      }

      progress.taskId = data.task_id
      listenProgress(data.task_id)
    } catch {
      progress.status = 'error'
      progress.error = '网络错误，请稍后重试'
    }
  }

  function listenProgress(taskId: string) {
    closeEventSource()
    eventSource = new EventSource(`/api/progress/${taskId}`)

    eventSource.onmessage = (e) => {
      const data = JSON.parse(e.data)

      if (data.status === 'heartbeat') return

      if (data.status === 'downloading') {
        progress.status = 'downloading'
        progress.percent = Math.min(data.percent || 0, 100)
        progress.speed = data.speed || ''
        progress.eta = data.eta || ''
      }

      if (data.status === 'merging') {
        progress.status = 'merging'
        progress.percent = 100
      }

      if (data.status === 'done') {
        closeEventSource()
        progress.status = 'done'
        progress.percent = 100
      }

      if (data.status === 'error') {
        closeEventSource()
        progress.status = 'error'
        progress.error = data.error || '未知错误'
      }
    }

    eventSource.onerror = () => {
      closeEventSource()
      progress.status = 'error'
      progress.error = '连接中断，请重试'
    }
  }

  onUnmounted(() => {
    closeEventSource()
  })

  return {
    progress,
    startDownload,
    resetProgress,
  }
}
