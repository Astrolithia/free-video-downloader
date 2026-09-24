<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useVideoPlayer } from '@/composables/useVideoPlayer'

const props = defineProps<{
  src: string
  poster?: string
}>()

const { seekTime, seekCounter } = useVideoPlayer()
const videoRef = ref<HTMLVideoElement | null>(null)
let pendingMetadataHandler: (() => void) | null = null

function clearPendingHandler() {
  const video = videoRef.value
  if (video && pendingMetadataHandler) {
    video.removeEventListener('loadedmetadata', pendingMetadataHandler)
  }
  pendingMetadataHandler = null
}

function applySeek() {
  const video = videoRef.value
  if (!video) return

  const seek = () => {
    const shouldResume = !video.paused
    video.currentTime = seekTime.value
    if (shouldResume) {
      video.play().catch(() => {})
    }
  }

  if (video.readyState >= 1) {
    clearPendingHandler()
    seek()
    return
  }

  clearPendingHandler()
  pendingMetadataHandler = () => {
    pendingMetadataHandler = null
    seek()
  }
  video.addEventListener('loadedmetadata', pendingMetadataHandler, { once: true })
}

watch(seekCounter, applySeek)
watch(() => props.src, () => {
  clearPendingHandler()
  const video = videoRef.value
  if (video) {
    video.load()
  }
  if (seekCounter.value > 0) {
    applySeek()
  }
})

onMounted(() => {
  const video = videoRef.value
  if (video) {
    video.load()
  }
  if (seekCounter.value > 0) {
    applySeek()
  }
})
onBeforeUnmount(clearPendingHandler)
</script>

<template>
  <div class="video-player-wrapper w-full bg-black">
    <video
      ref="videoRef"
      :src="src"
      controls
      :poster="poster"
      playsinline
      preload="auto"
      class="w-full aspect-video bg-black"
    />
  </div>
</template>
