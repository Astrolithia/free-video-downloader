<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAIFeatures, type SubtitleSegment } from '@/composables/useAIFeatures'

const { subtitleData, isLoadingSubtitle, subtitleError, fetchSubtitle } = useAIFeatures()

const searchQuery = ref('')

const filteredSubtitles = computed<SubtitleSegment[]>(() => {
  if (!subtitleData.value) return []
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return subtitleData.value.subtitles
  return subtitleData.value.subtitles.filter(s =>
    s.text.toLowerCase().includes(q)
  )
})

function formatTime(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function copyFullText() {
  if (!subtitleData.value?.full_text) return
  navigator.clipboard.writeText(subtitleData.value.full_text)
}

function downloadAsSRT() {
  if (!subtitleData.value?.subtitles.length) return
  let srt = ''
  subtitleData.value.subtitles.forEach((seg, i) => {
    const startH = Math.floor(seg.start / 3600)
    const startM = Math.floor((seg.start % 3600) / 60)
    const startS = Math.floor(seg.start % 60)
    const startMs = Math.round((seg.start % 1) * 1000)
    const endH = Math.floor(seg.end / 3600)
    const endM = Math.floor((seg.end % 3600) / 60)
    const endS = Math.floor(seg.end % 60)
    const endMs = Math.round((seg.end % 1) * 1000)
    srt += `${i + 1}\n`
    srt += `${String(startH).padStart(2, '0')}:${String(startM).padStart(2, '0')}:${String(startS).padStart(2, '0')},${String(startMs).padStart(3, '0')}`
    srt += ` --> `
    srt += `${String(endH).padStart(2, '0')}:${String(endM).padStart(2, '0')}:${String(endS).padStart(2, '0')},${String(endMs).padStart(3, '0')}\n`
    srt += `${seg.text}\n\n`
  })
  const blob = new Blob([srt], { type: 'text/plain;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'subtitles.srt'
  a.click()
  URL.revokeObjectURL(a.href)
}

function downloadAsTXT() {
  if (!subtitleData.value?.full_text) return
  const blob = new Blob([subtitleData.value.full_text], { type: 'text/plain;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'subtitles.txt'
  a.click()
  URL.revokeObjectURL(a.href)
}
</script>

<template>
  <div class="subtitle-view">
    <!-- Not loaded yet -->
    <div v-if="!subtitleData && !isLoadingSubtitle && !subtitleError" class="text-center py-10">
      <button class="ai-action-btn" @click="fetchSubtitle">
        <span class="mr-2">📝</span> 提取字幕
      </button>
      <p class="text-slate-400 text-sm mt-3">从视频平台获取字幕内容</p>
    </div>

    <!-- Loading -->
    <div v-else-if="isLoadingSubtitle" class="text-center py-10">
      <div class="spinner-dark mx-auto mb-3"></div>
      <p class="text-slate-500">正在提取字幕...</p>
    </div>

    <!-- Error -->
    <div v-else-if="subtitleError" class="text-center py-10">
      <p class="text-red-500 mb-3">{{ subtitleError }}</p>
      <button class="ai-action-btn" @click="fetchSubtitle">重试</button>
    </div>

    <!-- Subtitles loaded -->
    <div v-else-if="subtitleData">
      <div class="flex flex-wrap items-center gap-2 mb-4">
        <span class="text-xs text-slate-400 bg-slate-100 px-2 py-1 rounded-full">
          <template v-if="subtitleData.is_danmaku">弹幕</template>
          <template v-else>{{ subtitleData.language || '未知语言' }}</template>
          <template v-if="subtitleData.is_auto"> · 自动生成</template>
        </span>
        <span class="text-xs text-slate-400">{{ subtitleData.subtitles.length }} 条字幕</span>
        <div class="flex-1"></div>
        <button class="text-xs text-indigo-500 hover:text-indigo-700 font-medium" @click="copyFullText">复制全文</button>
        <button class="text-xs text-indigo-500 hover:text-indigo-700 font-medium" @click="downloadAsSRT">下载 SRT</button>
        <button class="text-xs text-indigo-500 hover:text-indigo-700 font-medium" @click="downloadAsTXT">下载 TXT</button>
      </div>

      <div class="mb-3">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索字幕内容..."
          class="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-400"
        />
      </div>

      <div class="subtitle-list">
        <div
          v-for="(seg, i) in filteredSubtitles"
          :key="i"
          class="subtitle-item"
        >
          <span class="subtitle-time">{{ formatTime(seg.start) }}</span>
          <span class="subtitle-text">{{ seg.text }}</span>
        </div>
        <p v-if="filteredSubtitles.length === 0" class="text-center text-slate-400 text-sm py-4">
          无匹配字幕
        </p>
      </div>
    </div>
  </div>
</template>
