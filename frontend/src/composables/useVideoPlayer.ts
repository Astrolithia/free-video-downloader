import { ref } from 'vue'

const seekTime = ref(0)
const seekCounter = ref(0)

function seekTo(seconds: number) {
  seekTime.value = seconds
  seekCounter.value++
}

export function useVideoPlayer() {
  return {
    seekTime,
    seekCounter,
    seekTo,
  }
}
