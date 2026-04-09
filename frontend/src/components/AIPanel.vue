<script setup lang="ts">
import { ref } from 'vue'
import SubtitleView from './SubtitleView.vue'
import SummaryView from './SummaryView.vue'
import ChatView from './ChatView.vue'
import MindMapView from './MindMapView.vue'

type TabId = 'subtitle' | 'summary' | 'chat' | 'mindmap'

const activeTab = ref<TabId>('subtitle')

const tabs: { id: TabId; label: string; icon: string }[] = [
  { id: 'subtitle', label: '字幕', icon: '📝' },
  { id: 'summary', label: '总结', icon: '✨' },
  { id: 'chat', label: 'AI 问答', icon: '💬' },
  { id: 'mindmap', label: '思维导图', icon: '🧠' },
]
</script>

<template>
  <section class="max-w-2xl mx-auto px-5 pb-12 fade-in-up">
    <div class="ai-panel">
      <div class="ai-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          :class="['ai-tab', { active: activeTab === tab.id }]"
          @click="activeTab = tab.id"
        >
          <span class="ai-tab-icon">{{ tab.icon }}</span>
          <span>{{ tab.label }}</span>
        </button>
      </div>

      <div class="ai-tab-content">
        <SubtitleView v-if="activeTab === 'subtitle'" />
        <SummaryView v-else-if="activeTab === 'summary'" />
        <ChatView v-else-if="activeTab === 'chat'" />
        <MindMapView v-else-if="activeTab === 'mindmap'" />
      </div>
    </div>
  </section>
</template>
