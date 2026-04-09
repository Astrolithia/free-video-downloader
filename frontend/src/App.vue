<script setup lang="ts">
import { ref, watch } from 'vue'
import NavBar from './components/NavBar.vue'
import HeroSection from './components/HeroSection.vue'
import VideoResult from './components/VideoResult.vue'
import DownloadProgress from './components/DownloadProgress.vue'
import AIPanel from './components/AIPanel.vue'
import FeatureGrid from './components/FeatureGrid.vue'
import PlatformList from './components/PlatformList.vue'
import { useVideoParser } from './composables/useVideoParser'
import { useDownloader } from './composables/useDownloader'
import { useAIFeatures } from './composables/useAIFeatures'

const url = ref('')
const { videoInfo, isParsing, parseError, parseVideo, debouncedParse } = useVideoParser()
const { progress, startDownload } = useDownloader()
const { setVideo } = useAIFeatures()

watch(videoInfo, (info) => {
  if (info) {
    setVideo(info.webpage_url, info.title)
  }
})

function onParse(inputUrl: string) {
  parseVideo(inputUrl)
}

function onPaste(inputUrl: string) {
  debouncedParse(inputUrl)
}

function onDownload(webpageUrl: string, formatId: string, audioId: string | null) {
  startDownload(webpageUrl, formatId, audioId)
}
</script>

<template>
  <NavBar />

  <HeroSection
    v-model:url="url"
    :is-parsing="isParsing"
    :error-msg="parseError"
    @parse="onParse"
    @paste="onPaste"
  />

  <VideoResult
    v-if="videoInfo"
    :info="videoInfo"
    @download="onDownload"
  />

  <DownloadProgress
    v-if="progress.status !== 'idle'"
    :progress="progress"
  />

  <AIPanel v-if="videoInfo" />

  <FeatureGrid />
  <PlatformList />

  <footer class="border-t border-slate-200 py-8 text-center text-sm text-slate-400 px-5">
    <p class="mb-2">⚠️ 本工具仅供个人学习和研究使用，请尊重版权，勿用于商业用途。</p>
    <p>FreeVidGrab &copy; 2025 &mdash; Powered by <a href="https://github.com/yt-dlp/yt-dlp" target="_blank" class="underline hover:text-slate-600">yt-dlp</a></p>
  </footer>
</template>
