<script setup lang="ts">
import { useAIFeatures } from '@/composables/useAIFeatures'

const { summaryContent, isLoadingSummary, generateSummary } = useAIFeatures()

function copySummary() {
  if (!summaryContent.value) return
  navigator.clipboard.writeText(summaryContent.value)
}
</script>

<template>
  <div class="summary-view">
    <!-- Not generated yet -->
    <div v-if="!summaryContent && !isLoadingSummary" class="text-center py-10">
      <button class="ai-action-btn" @click="generateSummary">
        <span class="mr-2">✨</span> 生成 AI 总结
      </button>
      <p class="text-slate-400 text-sm mt-3">AI 将基于视频字幕生成结构化总结</p>
    </div>

    <!-- Loading / streaming -->
    <div v-else>
      <div class="flex items-center justify-between mb-3">
        <div v-if="isLoadingSummary" class="flex items-center gap-2 text-sm text-indigo-500">
          <div class="spinner-dark w-4 h-4"></div>
          <span>正在生成...</span>
        </div>
        <span v-else-if="summaryContent.startsWith('错误')" class="text-sm text-red-500 font-medium">生成失败</span>
        <span v-else class="text-sm text-green-600 font-medium">生成完成</span>
        <div class="flex gap-2">
          <button
            v-if="summaryContent && !isLoadingSummary"
            class="text-xs text-indigo-500 hover:text-indigo-700 font-medium"
            @click="copySummary"
          >复制</button>
          <button
            v-if="!isLoadingSummary"
            class="text-xs text-indigo-500 hover:text-indigo-700 font-medium"
            @click="generateSummary"
          >重新生成</button>
        </div>
      </div>

      <div class="markdown-body" v-html="renderMarkdown(summaryContent)"></div>
    </div>
  </div>
</template>

<script lang="ts">
function renderMarkdown(text: string): string {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
    .replace(/<\/ul>\s*<ul>/g, '')
    .replace(/\n{2,}/g, '<br/><br/>')
    .replace(/\n/g, '<br/>')
}
</script>
