<script setup lang="ts">
import type { VideoFormat } from '@/composables/useVideoParser'

defineProps<{
  format: VideoFormat
  active: boolean
}>()

defineEmits<{
  select: []
}>()

function formatFileSize(bytes: number | null): string {
  if (!bytes) return ''
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>

<template>
  <div
    class="format-pill"
    :class="{ active }"
    @click="$emit('select')"
  >
    <span class="label">{{ format.label }}</span>
    <span class="meta">
      {{ format.ext.toUpperCase() }}{{ format.filesize ? ' · ' + formatFileSize(format.filesize) : '' }}
    </span>
  </div>
</template>
