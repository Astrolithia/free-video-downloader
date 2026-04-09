<script setup lang="ts">
const emit = defineEmits<{
  parse: [url: string]
  paste: [url: string]
}>()

const urlInput = defineModel<string>('url', { default: '' })

defineProps<{
  isParsing: boolean
  errorMsg: string
}>()

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') emit('parse', urlInput.value)
}

function onPaste() {
  setTimeout(() => emit('paste', urlInput.value), 0)
}
</script>

<template>
  <section class="pt-28 pb-12 sm:pt-36 sm:pb-20 text-center px-5">
    <div class="hero-glow"></div>
    <h1 class="text-4xl sm:text-5xl lg:text-6xl font-extrabold leading-tight mb-5">
      万能视频<span class="gradient-text">下载器</span>
    </h1>
    <p class="text-slate-500 text-base sm:text-lg max-w-xl mx-auto mb-10 leading-relaxed">
      粘贴链接，一键解析，极速下载。<br class="sm:hidden" />支持 YouTube、B 站、抖音等 <strong class="text-slate-700">1000+</strong> 平台
    </p>

    <div class="max-w-2xl mx-auto">
      <div class="url-input-wrapper flex items-center gap-2 p-1.5 rounded-2xl">
        <div class="flex items-center flex-1 bg-white rounded-xl px-4 py-3 gap-3">
          <svg class="w-5 h-5 text-slate-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
          <input
            v-model="urlInput"
            type="url"
            placeholder="粘贴视频链接，如 https://www.youtube.com/watch?v=..."
            class="flex-1 outline-none text-sm sm:text-base bg-transparent placeholder-slate-400"
            @keydown="onKeydown"
            @paste="onPaste"
          />
        </div>
        <button
          class="parse-btn shrink-0 px-6 sm:px-8 py-3 rounded-xl text-white font-semibold text-sm sm:text-base"
          :disabled="isParsing"
          @click="emit('parse', urlInput)"
        >
          <span v-if="isParsing" class="spinner"></span>
          <template v-else>解析视频</template>
        </button>
      </div>
      <p v-if="errorMsg" class="text-red-500 text-sm mt-3">{{ errorMsg }}</p>
    </div>
  </section>
</template>
