<script setup lang="ts">
import { ref, watch } from 'vue'
import type { VideoInfo, VideoFormat } from '@/composables/useVideoParser'
import FormatPill from './FormatPill.vue'

const props = defineProps<{
  info: VideoInfo
}>()

const emit = defineEmits<{
  download: [url: string, formatId: string, audioId: string | null]
}>()

const selectedFormat = ref<VideoFormat | null>(null)

watch(() => props.info, (newInfo) => {
  if (newInfo.formats.length > 0) {
    selectedFormat.value = newInfo.formats[0]
  } else {
    selectedFormat.value = null
  }
}, { immediate: true })

function formatDuration(sec: number | null): string {
  if (!sec) return ''
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function onDownload() {
  if (!selectedFormat.value) return
  emit(
    'download',
    props.info.webpage_url,
    selectedFormat.value.format_id,
    selectedFormat.value.best_audio_id,
  )
}
</script>

<template>
  <section class="max-w-2xl mx-auto px-5 pb-12 fade-in-up">
    <div class="result-card rounded-3xl overflow-hidden">
      <div class="relative">
        <img :src="info.thumbnail" :alt="info.title" class="w-full aspect-video object-cover bg-slate-200" />
        <span v-if="info.duration" class="absolute bottom-3 right-3 bg-black/70 text-white text-xs px-2 py-1 rounded-lg">
          {{ formatDuration(info.duration) }}
        </span>
      </div>
      <div class="p-5 sm:p-6">
        <h3 class="font-bold text-lg mb-1 line-clamp-2">{{ info.title }}</h3>
        <p v-if="info.uploader" class="text-slate-500 text-sm mb-4">上传者: {{ info.uploader }}</p>

        <div class="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-4">
          <template v-if="info.formats.length > 0">
            <FormatPill
              v-for="f in info.formats"
              :key="f.format_id"
              :format="f"
              :active="selectedFormat?.format_id === f.format_id"
              @select="selectedFormat = f"
            />
          </template>
          <p v-else class="col-span-full text-slate-400 text-sm">未检测到可下载的格式</p>
        </div>

        <button
          class="w-full download-btn py-3 rounded-xl text-white font-semibold text-base disabled:opacity-40 disabled:cursor-not-allowed"
          :disabled="!selectedFormat"
          @click="onDownload"
        >
          {{ selectedFormat ? `下载 ${selectedFormat.label} (${selectedFormat.ext.toUpperCase()})` : '选择清晰度后下载' }}
        </button>
      </div>
    </div>
  </section>
</template>
