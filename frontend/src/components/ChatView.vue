<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { useAIFeatures } from '@/composables/useAIFeatures'

const { chatMessages, isLoadingChat, sendChatMessage } = useAIFeatures()

const inputText = ref('')
const chatListRef = ref<HTMLElement | null>(null)

const quickQuestions = [
  '这个视频的核心观点是什么？',
  '请用简单的话总结一下',
  '视频中有哪些值得注意的细节？',
  '这个视频适合什么样的观众？',
]

function send() {
  const text = inputText.value.trim()
  if (!text || isLoadingChat.value) return
  inputText.value = ''
  sendChatMessage(text)
}

function askQuick(q: string) {
  if (isLoadingChat.value) return
  sendChatMessage(q)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

watch(
  () => chatMessages.value.length > 0 ? chatMessages.value[chatMessages.value.length - 1].content : '',
  () => {
    nextTick(() => {
      if (chatListRef.value) {
        chatListRef.value.scrollTop = chatListRef.value.scrollHeight
      }
    })
  },
)

function renderMarkdown(text: string): string {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
    .replace(/<\/ul>\s*<ul>/g, '')
    .replace(/\n{2,}/g, '<br/><br/>')
    .replace(/\n/g, '<br/>')
}
</script>

<template>
  <div class="chat-view">
    <!-- Empty state -->
    <div v-if="chatMessages.length === 0 && !isLoadingChat" class="text-center py-6">
      <p class="text-slate-500 mb-4">基于视频内容向 AI 提问</p>
      <div class="flex flex-wrap justify-center gap-2">
        <button
          v-for="q in quickQuestions"
          :key="q"
          class="quick-question-btn"
          @click="askQuick(q)"
        >
          {{ q }}
        </button>
      </div>
    </div>

    <!-- Chat messages -->
    <div v-else ref="chatListRef" class="chat-list">
      <div
        v-for="(msg, i) in chatMessages"
        :key="i"
        :class="['chat-bubble', msg.role === 'user' ? 'chat-user' : 'chat-assistant']"
      >
        <div class="chat-role">{{ msg.role === 'user' ? '你' : 'AI' }}</div>
        <div
          v-if="msg.role === 'assistant'"
          class="chat-content markdown-body"
          v-html="renderMarkdown(msg.content) || (isLoadingChat && i === chatMessages.length - 1 ? '<span class=&quot;typing-dot&quot;></span>' : '')"
        ></div>
        <div v-else class="chat-content">{{ msg.content }}</div>
      </div>
    </div>

    <!-- Input area -->
    <div class="chat-input-area">
      <textarea
        v-model="inputText"
        placeholder="输入你的问题..."
        rows="1"
        class="chat-input"
        @keydown="onKeydown"
      ></textarea>
      <button
        class="chat-send-btn"
        :disabled="!inputText.trim() || isLoadingChat"
        @click="send"
      >
        <span v-if="isLoadingChat" class="spinner-dark w-4 h-4"></span>
        <span v-else>发送</span>
      </button>
    </div>
  </div>
</template>
