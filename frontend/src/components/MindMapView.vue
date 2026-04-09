<script setup lang="ts">
import { ref, watch, nextTick, onUnmounted } from 'vue'
import { useAIFeatures } from '@/composables/useAIFeatures'

const { mindmapMarkdown, isLoadingMindmap, generateMindmap } = useAIFeatures()

const svgRef = ref<HTMLElement | null>(null)
let markmapInstance: any = null

async function renderMindmap(md: string) {
  if (!md || !svgRef.value || md.startsWith('错误')) return

  try {
    const { Transformer } = await import('markmap-lib')
    const { Markmap } = await import('markmap-view')

    const transformer = new Transformer()
    const { root } = transformer.transform(md)

    const svg = svgRef.value.querySelector('svg')
    if (!svg) return

    if (markmapInstance) {
      markmapInstance.setData(root)
      markmapInstance.fit()
    } else {
      markmapInstance = Markmap.create(svg as SVGElement, { autoFit: true }, root)
    }
  } catch (e) {
    console.error('Mindmap render error:', e)
  }
}

let renderTimer: ReturnType<typeof setTimeout> | null = null
watch(mindmapMarkdown, (md) => {
  if (!md) return
  if (renderTimer) clearTimeout(renderTimer)
  renderTimer = setTimeout(() => {
    nextTick(() => renderMindmap(md))
  }, 500)
})

function downloadSVG() {
  const svg = svgRef.value?.querySelector('svg')
  if (!svg) return
  const svgData = new XMLSerializer().serializeToString(svg)
  const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'mindmap.svg'
  a.click()
  URL.revokeObjectURL(a.href)
}

onUnmounted(() => {
  if (renderTimer) clearTimeout(renderTimer)
  markmapInstance = null
})
</script>

<template>
  <div class="mindmap-view">
    <!-- Not generated yet -->
    <div v-if="!mindmapMarkdown && !isLoadingMindmap" class="text-center py-10">
      <button class="ai-action-btn" @click="generateMindmap">
        <span class="mr-2">🧠</span> 生成思维导图
      </button>
      <p class="text-slate-400 text-sm mt-3">AI 将基于视频内容生成交互式思维导图</p>
    </div>

    <!-- Loading / Result -->
    <div v-else>
      <div class="flex items-center justify-between mb-3">
        <div v-if="isLoadingMindmap" class="flex items-center gap-2 text-sm text-indigo-500">
          <div class="spinner-dark w-4 h-4"></div>
          <span>正在生成...</span>
        </div>
        <span v-else-if="mindmapMarkdown.startsWith('错误')" class="text-sm text-red-500 font-medium">生成失败</span>
        <span v-else class="text-sm text-green-600 font-medium">生成完成</span>
        <div class="flex gap-2">
          <button
            v-if="!isLoadingMindmap && mindmapMarkdown"
            class="text-xs text-indigo-500 hover:text-indigo-700 font-medium"
            @click="downloadSVG"
          >导出 SVG</button>
          <button
            v-if="!isLoadingMindmap"
            class="text-xs text-indigo-500 hover:text-indigo-700 font-medium"
            @click="generateMindmap"
          >重新生成</button>
        </div>
      </div>

      <div v-if="mindmapMarkdown.startsWith('错误')" class="text-red-500 text-sm py-4">
        {{ mindmapMarkdown }}
      </div>
      <div v-else ref="svgRef" class="mindmap-container">
        <svg class="w-full" style="min-height: 400px;"></svg>
      </div>
    </div>
  </div>
</template>
