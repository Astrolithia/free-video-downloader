<script setup lang="ts">
import type { DownloadProgress } from '@/composables/useDownloader'

defineProps<{
  progress: DownloadProgress
}>()

function fileUrl(taskId: string): string {
  return `/api/file/${taskId}`
}
</script>

<template>
  <section class="max-w-2xl mx-auto px-5 pb-12 fade-in-up">
    <div class="result-card rounded-3xl p-6 sm:p-8 text-center">
      <div class="mb-4">
        <div class="text-4xl mb-2">
          <template v-if="progress.status === 'done'">✅</template>
          <template v-else-if="progress.status === 'error'">❌</template>
          <template v-else>⏳</template>
        </div>
        <p class="font-semibold text-lg">
          <template v-if="progress.status === 'downloading'">正在下载...</template>
          <template v-else-if="progress.status === 'merging'">正在合并音视频...</template>
          <template v-else-if="progress.status === 'done'">下载完成!</template>
          <template v-else-if="progress.status === 'error'">下载失败</template>
          <template v-else>准备中...</template>
        </p>
        <p class="text-slate-500 text-sm mt-1">
          <template v-if="progress.status === 'downloading'">
            <span v-if="progress.speed">{{ progress.speed }}</span>
            <span v-if="progress.speed && progress.eta">  ·  </span>
            <span v-if="progress.eta">剩余 {{ progress.eta }}</span>
          </template>
          <template v-else-if="progress.status === 'merging'">即将完成</template>
          <template v-else-if="progress.status === 'error'">{{ progress.error }}</template>
        </p>
      </div>

      <div class="progress-track rounded-full h-3 mb-4">
        <div
          class="progress-fill h-full rounded-full transition-all duration-300"
          :style="{ width: progress.percent + '%' }"
        ></div>
      </div>
      <p class="text-sm text-slate-500">{{ progress.percent.toFixed(1) }}%</p>

      <a
        v-if="progress.status === 'done'"
        :href="fileUrl(progress.taskId)"
        class="mt-4 inline-block save-btn px-8 py-3 rounded-xl text-white font-semibold text-base"
      >
        💾 保存到本地
      </a>
      <p v-if="progress.status === 'done'" class="mt-3 text-sm text-slate-500">
        下载完成后，封面区域会切换为页内播放器，并播放本次下载好的视频。
      </p>
    </div>
  </section>
</template>
